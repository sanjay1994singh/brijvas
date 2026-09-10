"""Privileged worker helpers; never execute from web request handlers."""
import ipaddress
import re
from pathlib import Path
import dns.resolver
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import normalize_domain


def check_dns(domain):
    hostname = normalize_domain(domain.hostname)
    expected = settings.SAAS_SERVER_IP
    if not expected or not ipaddress.ip_address(expected).is_global:
        raise ValidationError('Platform server IP is not configured.')
    addresses = []
    for kind in ('A', 'AAAA'):
        try:
            addresses.extend(str(answer) for answer in dns.resolver.resolve(hostname, kind, lifetime=5))
        except dns.resolver.NoAnswer:
            pass
    if not addresses or any(address != expected for address in addresses):
        raise ValidationError('Point all A records to the platform IP and remove conflicting AAAA records.')
    if not domain.is_platform:
        answers = dns.resolver.resolve(domain.txt_name, 'TXT', lifetime=5)
        values = [''.join(part.decode() for part in answer.strings) for answer in answers]
        if domain.txt_value not in values:
            raise ValidationError('Keep the ownership TXT record in DNS before HTTPS activation.')


def assert_no_conflict(hostname, own_paths, directory=Path('/etc/apache2/sites-enabled')):
    for path in directory.glob('*'):
        if path.resolve() in {p.resolve() for p in own_paths}:
            continue
        text = path.read_text()
        for line in text.splitlines():
            parts = line.strip().split()
            if parts and parts[0].lower() in ('servername', 'serveralias'):
                if hostname in [value.lower() for value in parts[1:]]:
                    raise ValidationError('This hostname is already assigned to another server website. Contact support.')


def http_config(hostname):
    hostname = normalize_domain(hostname)
    return f'''# Managed by Property Studio domain worker
<VirtualHost *:80>
 ServerName {hostname}
 Alias /.well-known/acme-challenge/ /var/www/brijvas-saas/acme/.well-known/acme-challenge/
 <Directory /var/www/brijvas-saas/acme>
  Require all granted
  Options -Indexes
 </Directory>
 RewriteEngine on
 RewriteCond %{{REQUEST_URI}} !^/\\.well-known/acme-challenge/
 RewriteRule ^ https://{hostname}%{{REQUEST_URI}} [R=302,L]
</VirtualHost>
'''


def https_config(hostname, cert_name):
    hostname = normalize_domain(hostname)
    if not re.fullmatch(r'property-domain-[0-9]+', cert_name):
        raise ValidationError('Invalid certificate identifier.')
    template = (Path(settings.BASE_DIR) / 'deploy/propertystudio-le-ssl.conf').read_text()
    template = template.replace('ServerName propertystudio.live-app.in', f'ServerName {hostname}')
    template = template.replace('/live/propertystudio.live-app.in/', f'/live/{cert_name}/')
    template = template.replace('    ProxyPass /static/ !', '''    Alias /.well-known/acme-challenge/ /var/www/brijvas-saas/acme/.well-known/acme-challenge/
    <Directory /var/www/brijvas-saas/acme>
        Require all granted
        Options -Indexes
    </Directory>
    ProxyPass /.well-known/acme-challenge/ !
    ProxyPass /static/ !''')
    return '# Managed by Property Studio domain worker\n' + template
