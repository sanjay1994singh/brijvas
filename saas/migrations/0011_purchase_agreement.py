from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


DEFAULT_AGREEMENT = """सेवा लेने से पहले कृपया Vistaflo वेबसाइट प्लान की खरीद और उपयोग शर्तें ध्यान से पढ़ें।

यह subscription SHRI INFOWAVE PRIVATE LIMITED द्वारा संचालित Vistaflo property website platform के लिए है। आपके चुने हुए plan के अनुसार property listing limit, staff/member access, custom domain support, billing period, discount, GST और payable amount checkout पर दिखाया जाता है।

Trial enabled होने पर workspace trial period तक access रहेगा। Trial disabled होने पर workspace/account paid payment verification के बाद ही activate होगा। Payment failed, cancelled या unverified रहने पर paid access activate नहीं होगा।

Plan upgrade/renewal पर current paid amount/credit, discount और GST system calculation के अनुसार payment summary में दिखेगा। Invoice successful payment के बाद generate होगा।

Domain, Google Analytics, Google Ads, Search Console verification, WhatsApp notifications और third-party services customer द्वारा दिए गए valid details/settings पर depend करते हैं। DNS propagation, provider delays या third-party policy changes के लिए platform responsible नहीं होगा।

Property content, images, pricing, address, owner details और enquiries की correctness customer/business owner की responsibility होगी। Vistaflo software, hosting coordination, billing records और technical support provide करता है।

Refund, cancellation, support और dispute requests platform policies और applicable Indian law के अनुसार handle होंगे। इस agreement को accept करके आप confirm करते हैं कि आपने plan, amount, billing period और service conditions समझ ली हैं।"""


def seed_purchase_agreement(apps, schema_editor):
    PlatformPurchaseAgreement = apps.get_model("saas", "PlatformPurchaseAgreement")
    PlatformPurchaseAgreement.objects.get_or_create(
        is_active=True,
        title="Plan Purchase Agreement",
        defaults={
            "content": DEFAULT_AGREEMENT,
            "checkbox_label": "I have read and agree to the plan purchase terms.",
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("saas", "0010_billing_seller_details"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformPurchaseAgreement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Plan Purchase Agreement", max_length=180)),
                ("content", models.TextField()),
                ("checkbox_label", models.CharField(default="I have read and agree to the plan purchase terms.", max_length=255)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-is_active", "-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="PurchaseAgreementAcceptance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("agreement_title", models.CharField(max_length=180)),
                ("agreement_content", models.TextField()),
                ("checkbox_label", models.CharField(max_length=255)),
                ("plan_name", models.CharField(blank=True, max_length=120)),
                ("amount", models.PositiveIntegerField(default=0)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("accepted_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("agreement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acceptances", to="saas.platformpurchaseagreement")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="purchase_agreement_acceptances", to="saas.billingorder")),
                ("pending_signup", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="purchase_agreement_acceptances", to="saas.pendingsignup")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="purchase_agreement_acceptances", to="saas.tenant")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="vistaflo_purchase_agreement_acceptances", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-accepted_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="purchaseagreementacceptance",
            index=models.Index(fields=["user", "accepted_at"], name="saas_purcha_user_id_a9e08f_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseagreementacceptance",
            index=models.Index(fields=["tenant", "accepted_at"], name="saas_purcha_tenant__28fb1a_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseagreementacceptance",
            index=models.Index(fields=["order", "accepted_at"], name="saas_purcha_order_i_2747bd_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseagreementacceptance",
            index=models.Index(fields=["pending_signup", "accepted_at"], name="saas_purcha_pending_69184b_idx"),
        ),
        migrations.RunPython(seed_purchase_agreement, migrations.RunPython.noop),
    ]
