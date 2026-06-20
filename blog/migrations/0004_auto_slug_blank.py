from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0003_blog_updated_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="blog",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
        migrations.AlterField(
            model_name="blogcategory",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
    ]
