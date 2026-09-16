import uuid
from pathlib import Path
import bleach
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from PIL import Image, UnidentifiedImageError
from .models import Tenant
from .services import subscription_for


def sanitize_html(value):
    return bleach.clean(value, tags={'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'a', 'ul', 'ol', 'li', 'blockquote', 'h2', 'h3', 'h4', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'figure', 'figcaption', 'img'}, attributes={'a': ['href', 'title'], 'img': ['src', 'alt', 'width', 'height'], 'td': ['colspan', 'rowspan'], 'th': ['colspan', 'rowspan']}, protocols=['http', 'https'], strip=True)


def tenant_upload_path(instance, filename):
    tenant = getattr(instance, 'tenant', None)
    if tenant is None and hasattr(instance, 'property'):
        tenant = instance.property.tenant
    if tenant is None and hasattr(instance, 'blog'):
        tenant = instance.blog.tenant
    if tenant is None:
        raise ValidationError('An upload must belong to a business.')
    suffix = Path(filename).suffix.lower()
    return f'tenants/{tenant.uuid}/{instance._meta.model_name}/{uuid.uuid4().hex}{suffix}'


def ensure_storage(tenant, incoming_size):
    subscription_for(tenant)


@login_required
@require_POST
def editor_upload(request):
    if not request.membership or not request.membership.can_list:
        raise PermissionDenied('Approved business membership required.')
    upload = request.FILES.get('upload')
    if not upload or upload.size > 5 * 1024 * 1024:
        return JsonResponse({'error': {'message': 'Select an image up to 5 MB.'}}, status=400)
    try:
        img = Image.open(upload)
        if img.format not in ('JPEG', 'PNG', 'WEBP') or img.width * img.height > 25_000_000:
            raise ValueError()
        img.verify()
        upload.seek(0)
        with transaction.atomic():
            Tenant.objects.select_for_update().get(pk=request.tenant.pk)
            ensure_storage(request.tenant, upload.size)
            suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[img.format]
            name = default_storage.save(f'tenants/{request.tenant.uuid}/editor/{uuid.uuid4().hex}{suffix}', upload)
        return JsonResponse({'url': default_storage.url(name)})
    except (ValidationError, ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return JsonResponse({'error': {'message': 'Upload rejected. Check the image and your storage allowance.'}}, status=400)
