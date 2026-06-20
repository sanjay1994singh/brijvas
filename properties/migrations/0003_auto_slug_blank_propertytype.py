from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0002_compareproperty_propertyreview_wishlist"),
    ]

    operations = [
        migrations.AlterField(
            model_name="propertytype",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
    ]
