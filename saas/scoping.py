from django.core.exceptions import PermissionDenied


def scoped(model, tenant):
    """Explicit, fail-closed queryset for every customer-facing entry point."""
    if tenant is None:
        return model.objects.none()
    names = {field.name for field in model._meta.fields}
    if 'tenant' in names:
        return model.objects.filter(tenant=tenant).order_by('pk')
    if 'property' in names:
        return model.objects.filter(property__tenant=tenant).order_by('pk')
    if 'blog' in names:
        return model.objects.filter(blog__tenant=tenant).order_by('pk')
    raise ValueError(f'No tenant ownership path for {model.__name__}')


def require_manager(request):
    if not getattr(request, 'membership', None) or not request.membership.can_manage:
        raise PermissionDenied('Business administrator access required.')
    return request.membership

