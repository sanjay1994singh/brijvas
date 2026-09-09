import ssl
import socket
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from saas.models import Domain, Tenant, AuditEvent


class Command(BaseCommand):
    help = 'Activate a verified domain after DNS/proxy/certificate setup, checking real TLS hostname validation.'

    def add_arguments(self, parser):
        parser.add_argument('hostname')

    def handle(self, *args, **options):
        domain = Domain.objects.filter(hostname=options['hostname'], is_verified=True).first()
        if not domain:
            raise CommandError('A TXT-verified domain is required.')
        import ipaddress
        try:
            addresses = socket.getaddrinfo(domain.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise CommandError('Domain must resolve only to public addresses.')
            with socket.create_connection(addresses[0][4][:2], timeout=10) as sock:
                with ssl.create_default_context().wrap_socket(sock, server_hostname=domain.hostname):
                    pass
        except (OSError, ssl.SSLError) as exc:
            raise CommandError('HTTPS verification failed. Finish certificate/proxy setup first.') from exc
        with transaction.atomic():
            Tenant.objects.select_for_update().get(pk=domain.tenant_id)
            Domain.objects.filter(tenant_id=domain.tenant_id).update(is_primary=False)
            domain.ssl_ready, domain.is_primary = True, True
            domain.save(update_fields=['ssl_ready', 'is_primary'])
            AuditEvent.objects.create(tenant_id=domain.tenant_id, action='domain.activated', detail=domain.hostname)
        self.stdout.write(self.style.SUCCESS('HTTPS domain activated. Confirm the reverse proxy routes it to this application.'))
