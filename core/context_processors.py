from core.models import SiteSetting
from properties.models import PropertyType


def site_settings(request):
    setting = SiteSetting.objects.first()

    return {
        "site_setting": setting
    }


def property_types(request):
    return {
        "property_types": PropertyType.objects.all()
    }
