from django.urls import path
from . import views
from accounts.views import user_login

urlpatterns = [
    path('accounts/signup/', views.signup, name='saas_signup'),
    path('accounts/signup/<uuid:signup_id>/checkout/', views.pending_checkout, name='saas_pending_checkout'),
    path('accounts/signup/<uuid:signup_id>/payment/verify/', views.pending_payment_verify, name='saas_pending_payment_verify'),
    path('accounts/login/', user_login, name='saas_login'),
    path('accounts/workspaces/', views.workspaces, name='saas_workspaces'),
    path('billing/webhook/razorpay/', views.webhook, name='saas_webhook'),
    path('billing/invoices/whatsapp/<str:token>.pdf', views.whatsapp_invoice_pdf, name='saas_whatsapp_invoice_pdf'),
    path('manage/<slug:slug>/', views.business, name='saas_business'),
    path('manage/<slug:slug>/settings/', views.branding, name='saas_branding'),
    path('manage/<slug:slug>/members/', views.members, name='saas_members'),
    path('manage/<slug:slug>/members/<int:pk>/', views.member_action, name='saas_member_action'),
    path('manage/<slug:slug>/listings/', views.listings, name='saas_listings'),
    path('manage/<slug:slug>/listings/<int:pk>/', views.listing_action, name='saas_listing_action'),
    path('manage/<slug:slug>/leads/', views.leads, name='saas_leads'),
    path('manage/<slug:slug>/domains/', views.domains, name='saas_domains'),
    path('manage/<slug:slug>/domains/<int:pk>/verify/', views.verify_domain, name='saas_verify_domain'),
    path('manage/<slug:slug>/checkout/', views.checkout, name='saas_checkout'),
    path('manage/<slug:slug>/payment/verify/', views.payment_verify, name='saas_payment_verify'),
    path('manage/<slug:slug>/invoices/<uuid:order_uuid>/', views.invoice, name='saas_invoice'),
    path('manage/<slug:slug>/invoices/<uuid:order_uuid>/download/', views.invoice_download, name='saas_invoice_download'),
]
