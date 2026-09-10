import fcntl
import os
import secrets
import subprocess
from datetime import timedelta
from pathlib import Path
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from saas.models import Domain, Tenant, AuditEvent
from saas.domain_provisioning import check_dns, assert_no_conflict, http_config, https_config


class Command(BaseCommand):
    help = 'Root-only, serialized DNS/Apache/Certbot worker for requested customer hosts.'

    def add_arguments(self, parser):
        parser.add_argument('--domain-id', type=int)

    def handle(self, *args, **options):
        if os.geteuid() != 0 or str(settings.BASE_DIR) != '/var/www/brijvas-saas':
            raise CommandError('Run only as the production domain service operator.')
        with open('/run/property-studio-domains.lock', 'w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            domains = Domain.objects.filter(provisioning_requested=True, is_verified=True, ssl_ready=False).exclude(tenant__status='suspended')
            if options['domain_id']:
                domains = domains.filter(pk=options['domain_id'])
            else:
                domains = domains.filter(Q(last_attempt_at__isnull=True) | Q(last_attempt_at__lt=timezone.now()-timedelta(minutes=30)))
            for domain in domains.order_by('last_attempt_at', 'pk')[:5]:
                domain.last_attempt_at = timezone.now()
                domain.save(update_fields=['last_attempt_at'])
                try:
                    self.activate(domain)
                except Exception as exc:
                    # Fixed action output only; no credential-bearing subprocess output stored.
                    from django.core.exceptions import ValidationError
                    error = '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'HTTPS setup could not complete. Check DNS or contact support; automatic retry is scheduled.'
                    Domain.objects.filter(pk=domain.pk).update(error=error[:300])
                    self.stderr.write(f'Domain {domain.pk}: {type(exc).__name__}: setup pending')

    def run(self, args):
        subprocess.run(args, check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def activate(self, domain):
        root = settings.SAAS_CUSTOMER_DOMAIN_ROOT
        if domain.is_platform and domain.hostname != f'{domain.tenant.slug}.{root}':
            raise CommandError('Platform hostname does not match tenant.')
        check_dns(domain)
        available = Path('/etc/apache2/sites-available')
        enabled = Path('/etc/apache2/sites-enabled')
        http = available / f'00-property-domain-{domain.pk}.conf'
        https = available / f'00-property-domain-{domain.pk}-ssl.conf'
        assert_no_conflict(domain.hostname, [http, https])
        for path in (http, https):
            if path.exists() and not path.read_text().startswith('# Managed by Property Studio domain worker'):
                raise CommandError('Refusing to overwrite unmanaged configuration.')
        challenge = Path('/var/www/brijvas-saas/acme/.well-known/acme-challenge')
        challenge.mkdir(parents=True, exist_ok=True)
        http.write_text(http_config(domain.hostname))
        (enabled/http.name).symlink_to(http) if not (enabled/http.name).exists() else None
        self.run(['apache2ctl', 'configtest'])
        self.run(['systemctl', 'reload', 'apache2'])
        cert_name = f'property-domain-{domain.pk}'
        self.run(['certbot', 'certonly', '--webroot', '-w', '/var/www/brijvas-saas/acme',
                  '--cert-name', cert_name, '-d', domain.hostname, '--non-interactive', '--keep-until-expiring',
                  '--deploy-hook', 'systemctl reload apache2'])
        https.write_text(https_config(domain.hostname, cert_name))
        (enabled/https.name).symlink_to(https) if not (enabled/https.name).exists() else None
        try:
            self.run(['apache2ctl', 'configtest'])
            self.run(['systemctl', 'reload', 'apache2'])
        except Exception:
            (enabled/https.name).unlink(missing_ok=True)
            raise
        # Check public TLS AND routing to this application's webroot before publishing URL.
        token = secrets.token_hex(24)
        probe = challenge / ('probe-' + token)
        probe.write_text(token)
        try:
            response = requests.get(f'https://{domain.hostname}/.well-known/acme-challenge/{probe.name}', timeout=15, allow_redirects=False)
            if response.status_code != 200 or response.text != token:
                raise CommandError('Public HTTPS routing verification failed.')
        finally:
            probe.unlink(missing_ok=True)
        # Keep Django's host protection explicit; never use a global wildcard.
        import shutil
        hostfile = Path('/etc/property-studio/allowed-hosts')
        hosts = hostfile.read_text().splitlines() if hostfile.exists() else []
        if '*' in hosts:
            raise CommandError('Explicit host allowlist required.')
        if domain.hostname not in hosts:
            hosts.append(domain.hostname)
            hostfile.parent.mkdir(mode=0o750, exist_ok=True)
            shutil.chown(hostfile.parent, user='root', group='www-data')
            temporary = hostfile.with_suffix('.tmp')
            temporary.write_text('\n'.join(hosts) + '\n')
            shutil.chown(temporary, user='root', group='www-data')
            os.chmod(temporary, 0o640)
            temporary.replace(hostfile)
            self.run(['systemctl', 'restart', 'brijvas-saas'])
        with transaction.atomic():
            Tenant.objects.select_for_update().get(pk=domain.tenant_id)
            current = Domain.objects.select_for_update().get(pk=domain.pk)
            if not current.is_verified or not current.provisioning_requested:
                raise CommandError('Activation request changed.')
            primary = not current.is_platform or not Domain.objects.filter(tenant_id=current.tenant_id, is_primary=True, ssl_ready=True).exists()
            if primary:
                Domain.objects.filter(tenant_id=current.tenant_id).update(is_primary=False)
            current.ssl_ready = True
            current.is_primary = primary
            current.provisioning_requested = False
            current.error = ''
            current.save(update_fields=['ssl_ready', 'is_primary', 'provisioning_requested', 'error'])
            AuditEvent.objects.create(tenant_id=current.tenant_id, action='domain.automatically_activated', detail=current.hostname)
        self.stdout.write(f'Domain {domain.pk}: HTTPS active')
