from django.db import migrations


DEFAULT_TYPES = ("Plot", "Flat", "Villa", "Farm House", "Commercial")


def type_slug(name):
    return name.strip().lower().replace(" ", "-") or "property"


def move_to_global_property_types(apps, schema_editor):
    PropertyType = apps.get_model("properties", "PropertyType")
    Property = apps.get_model("properties", "Property")

    for title in DEFAULT_TYPES:
        PropertyType.objects.get_or_create(
            tenant=None,
            slug=type_slug(title),
            defaults={"name": title},
        )

    for property_type in list(PropertyType.objects.exclude(tenant=None).order_by("pk")):
        slug = property_type.slug or type_slug(property_type.name)
        global_type, _ = PropertyType.objects.get_or_create(
            tenant=None,
            slug=slug,
            defaults={"name": property_type.name},
        )
        Property.objects.filter(property_type=property_type).update(property_type=global_type)

    PropertyType.objects.exclude(tenant=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0016_alter_property_featured_image"),
    ]

    operations = [
        migrations.RunPython(move_to_global_property_types, migrations.RunPython.noop),
    ]
