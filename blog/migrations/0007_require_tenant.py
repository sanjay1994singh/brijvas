from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('blog', '0006_blog_tenant_blogcategory_tenant_and_more'), ('saas', '0002_backfill_brijvas')]
    operations = [migrations.AlterField(model_name=name, name='tenant', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='saas.tenant')) for name in ['blog', 'blogcategory']]
