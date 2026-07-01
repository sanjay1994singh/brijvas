from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


SQFT_PER_GAJ = Decimal("9")
SQFT_PER_SQ_METER = Decimal("10.7639")
SQFT_PER_ACRE = Decimal("43560")
SQFT_PER_BIGHA = Decimal("27225")


def rounded_area(value):
    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def rounded_land_area(value):
    return Decimal(value).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP
    )


def base_sqft(property_obj):
    area = Decimal(property_obj.area)
    unit = property_obj.area_unit

    if unit == "gaj":
        return area * SQFT_PER_GAJ
    if unit == "sq_meter":
        return area * SQFT_PER_SQ_METER
    if unit == "acre":
        return area * SQFT_PER_ACRE
    if unit == "bigha":
        return area * SQFT_PER_BIGHA

    return area


def backfill_more_area_values(apps, schema_editor):
    Property = apps.get_model("properties", "Property")

    for property_obj in Property.objects.exclude(area__isnull=True):
        sqft = base_sqft(property_obj)
        Property.objects.filter(pk=property_obj.pk).update(
            area_sqft=rounded_area(sqft),
            area_gaj=rounded_area(sqft / SQFT_PER_GAJ),
            area_sq_meter=rounded_area(sqft / SQFT_PER_SQ_METER),
            area_acre=rounded_land_area(sqft / SQFT_PER_ACRE),
            area_bigha=rounded_land_area(sqft / SQFT_PER_BIGHA),
        )


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0007_property_auto_seo_area_units"),
    ]

    operations = [
        migrations.AlterField(
            model_name="property",
            name="area_unit",
            field=models.CharField(
                choices=[
                    ("sqft", "Sqft"),
                    ("gaj", "Gaj"),
                    ("sq_meter", "Sq Meter"),
                    ("acre", "Acre"),
                    ("bigha", "Bigha"),
                ],
                default="sqft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="area_sq_meter",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                editable=False,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="area_acre",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                editable=False,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="area_bigha",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                editable=False,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_more_area_values,
            migrations.RunPython.noop,
        ),
    ]
