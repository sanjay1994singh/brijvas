# Generated manually after local Python environment could not import Django.

import django_ckeditor_5.fields
from django.db import migrations, models
from decimal import Decimal, ROUND_HALF_UP


def backfill_area_values(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')

    for property_obj in Property.objects.exclude(area__isnull=True):
        area = Decimal(property_obj.area).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )

        if property_obj.area_unit == 'gaj':
            area_gaj = area
            area_sqft = (area * Decimal('9')).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP,
            )
        else:
            area_sqft = area
            area_gaj = (area / Decimal('9')).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP,
            )

        Property.objects.filter(pk=property_obj.pk).update(
            area_sqft=area_sqft,
            area_gaj=area_gaj,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0006_remove_propertyview_properties__propert_30d0e5_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='title',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='property',
            name='address',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='property',
            name='description',
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True),
        ),
        migrations.AlterField(
            model_name='property',
            name='area_unit',
            field=models.CharField(
                choices=[
                    ('sqft', 'Sqft'),
                    ('gaj', 'Gaj'),
                ],
                default='sqft',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='property',
            name='area_sqft',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                editable=False,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='property',
            name='area_gaj',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                editable=False,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_area_values,
            migrations.RunPython.noop,
        ),
    ]
