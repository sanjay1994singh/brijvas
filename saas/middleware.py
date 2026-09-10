from urllib.parse import urlsplit
from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.urls import get_script_prefix, set_script_prefix
import re
from .models import Domain, Membership, Tenant


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        original_prefix = get_script_prefix()
        try:
            return self.resolve(request)
        finally:
            set_script_prefix(original_prefix)

    def resolve(self, request):
        hostname = request.get_host().split(':')[0].lower().rstrip('.')
        base_host = urlsplit(settings.SAAS_BASE_URL).hostname
        request.tenant = None
        request.membership = None
        platform_hosts = set(settings.SAAS_PLATFORM_HOSTS)
        path_match = re.match(r'^/sites/([a-z0-9-]+)(/.*)?$', request.path_info)
        if hostname in platform_hosts and path_match:
            request.tenant = Tenant.objects.filter(slug=path_match.group(1)).first()
            if not request.tenant:
                return HttpResponseNotFound('This website has not been configured.')
            prefix = '/sites/' + path_match.group(1)
            request.path_info = path_match.group(2) or '/'
            request.META['SCRIPT_NAME'] = prefix
            set_script_prefix(prefix)
        elif hostname in platform_hosts and settings.SAAS_ROOT_TENANT and not request.path_info.startswith(('/saas/', '/admin/')):
            request.tenant = Tenant.objects.filter(slug=settings.SAAS_ROOT_TENANT).first()
        if hostname not in platform_hosts:
            if hostname.endswith('.' + base_host):
                slug = hostname[:-(len(base_host) + 1)]
                request.tenant = Tenant.objects.filter(slug=slug).first()
            else:
                domain = Domain.objects.select_related('tenant').filter(hostname=hostname, is_verified=True, ssl_ready=True).first()
                request.tenant = domain.tenant if domain else None
            if request.tenant is None:
                return HttpResponseNotFound('This website has not been configured.')
            if request.tenant.status == 'suspended':
                return HttpResponseForbidden('This website is currently unavailable.')
        if request.tenant and request.tenant.status == 'suspended':
            return HttpResponseForbidden('This website is currently unavailable.')
        if request.tenant and request.user.is_authenticated:
            request.membership = Membership.objects.filter(tenant=request.tenant, user=request.user, is_active=True).first()
        if request.path_info.startswith('/admin/'):
            if request.tenant or (request.user.is_authenticated and not request.user.is_superuser):
                return HttpResponseForbidden('Platform administration is restricted.')
        if request.path_info.startswith('/auth/'):
            # Google OAuth is opt-in until callbacks for the production host are configured.
            if not settings.SAAS_GOOGLE_LOGIN_ENABLED:
                return HttpResponseNotFound('Google login is not configured. Use password login.')
        if request.tenant and request.path_info.startswith(('/dashboard/', '/ckeditor5/')):
            if request.user.is_authenticated and request.membership is None:
                return HttpResponseForbidden('You do not belong to this business.')
        if request.tenant and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if request.user.is_authenticated and not request.membership and not request.path_info.startswith('/accounts/'):
                return HttpResponseForbidden('You do not belong to this business.')
        if not request.tenant and not request.path_info.startswith(('/saas/', '/admin/', '/accounts/', '/static/', '/media/', '/auth/')) and request.path_info != '/':
            return HttpResponseNotFound('Open your business website to access this page.')
        return self.get_response(request)


class PublicRateLimitMiddleware:
    """Shared Redis counters for public write endpoints; trust only local reverse proxy."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.SAAS_RATE_LIMIT_ENABLED and request.method == 'POST':
            path = request.path_info
            limited = ('/saas/signup/', '/saas/login/', '/accounts/login/', '/accounts/register/', '/accounts/password-reset/', '/contact/')
            if path in limited or path.startswith('/properties/'):
                import hashlib
                from django.core.cache import cache
                from django.http import HttpResponse
                address = request.META.get('REMOTE_ADDR', '')
                if address in ('127.0.0.1', '::1') and getattr(settings, 'SECURE_PROXY_SSL_HEADER', None):
                    address = request.META.get('HTTP_X_FORWARDED_FOR', address).split(',')[-1].strip()
                key = 'public-write:' + hashlib.sha256(address.encode()).hexdigest()
                try:
                    if cache.add(key, 1, timeout=60):
                        count = 1
                    else:
                        try:
                            count = cache.incr(key)
                        except ValueError:
                            cache.set(key, 1, timeout=60)
                            count = 1
                except Exception:
                    return HttpResponse('Please retry shortly.', status=503)
                if count > 30:
                    response = HttpResponse('Too many requests. Please retry in a minute.', status=429)
                    response['Retry-After'] = '60'
                    return response
        return self.get_response(request)
