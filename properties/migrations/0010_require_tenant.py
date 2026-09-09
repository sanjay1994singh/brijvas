from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('properties', '0009_amenity_tenant_property_tenant_propertytype_tenant_and_more'), ('saas', '0002_backfill_brijvas')]
    operations = [migrations.AlterField(model_name=name, name='tenant', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='saas.tenant')) for name in ['amenity', 'property', 'propertytype']]
