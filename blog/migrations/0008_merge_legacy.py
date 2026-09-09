from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [["blog","0007_require_tenant"],["blog","0006_alter_blog_id_alter_blogcategory_id_and_more"]]
    dependencies = [tuple(item) for item in dependencies]
    operations = []

