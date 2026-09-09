from saas.scoping import scoped
from django.conf import settings
from core.models import SiteSetting
from properties.models import PropertyType


def site_settings(request):
    setting = scoped(SiteSetting, request.tenant).first()

    return {
        "site_setting": setting,
        "google_login_enabled": settings.SAAS_GOOGLE_LOGIN_ENABLED,
        "can_manage_business": bool(request.membership and request.membership.can_manage),
        "can_manage_listings": bool(request.membership and request.membership.can_list),
    }


def property_types(request):
    return {
        "property_types": scoped(PropertyType, request.tenant).all()
    }
