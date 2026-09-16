from django.db import migrations, models


def seed_billing_details(apps, schema_editor):
    BillingSetting = apps.get_model('saas', 'BillingSetting')
    setting, _ = BillingSetting.objects.get_or_create(pk=1)
    setting.business_name = 'SHRI INFOWAVE PRIVATE LIMITED'
    setting.business_address = '101 Govind Kund Tila, Radha Niwas, Vrindaban, Mathura, Uttar Pradesh, India'
    setting.gstin = '09ABUCS7544P1Z2'
    setting.pan = 'ABUCS7544P'
    setting.cin = 'U62012UW2026PTC257361'
    setting.support_email = 'shriinfowaveprivatelimited@gmail.com'
    setting.whatsapp_number = '918279408396'
    setting.save()


class Migration(migrations.Migration):

    dependencies = [
        ('saas', '0009_billingsetting_billingorder_discount_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingsetting',
            name='cin',
            field=models.CharField(blank=True, default='U62012UW2026PTC257361', max_length=32),
        ),
        migrations.AddField(
            model_name='billingsetting',
            name='pan',
            field=models.CharField(blank=True, default='ABUCS7544P', max_length=20),
        ),
        migrations.AddField(
            model_name='billingsetting',
            name='support_email',
            field=models.EmailField(blank=True, default='shriinfowaveprivatelimited@gmail.com', max_length=254),
        ),
        migrations.AddField(
            model_name='billingsetting',
            name='whatsapp_number',
            field=models.CharField(blank=True, default='918279408396', max_length=20),
        ),
        migrations.AlterField(
            model_name='billingsetting',
            name='business_address',
            field=models.TextField(default='101 Govind Kund Tila, Radha Niwas, Vrindaban, Mathura, Uttar Pradesh, India'),
        ),
        migrations.AlterField(
            model_name='billingsetting',
            name='business_name',
            field=models.CharField(default='SHRI INFOWAVE PRIVATE LIMITED', max_length=160),
        ),
        migrations.AlterField(
            model_name='billingsetting',
            name='gstin',
            field=models.CharField(blank=True, default='09ABUCS7544P1Z2', max_length=32),
        ),
        migrations.RunPython(seed_billing_details, migrations.RunPython.noop),
    ]
