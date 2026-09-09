from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [["core","0004_require_tenant"],["core","0003_alter_contact_id_alter_sitesetting_id"]]
    dependencies = [tuple(item) for item in dependencies]
    operations = []

