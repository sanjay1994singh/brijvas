from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0003_contact_tenant_sitesetting_about_text_and_more'), ('saas', '0002_backfill_brijvas')]
    operations = [migrations.AlterField(model_name=name, name='tenant', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='saas.tenant')) for name in ['contact', 'sitesetting']]
