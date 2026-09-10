from django.urls import path
from . import views
from accounts.views import user_login

urlpatterns = [
    path('', views.index, name='saas_home'),
    path('signup/', views.signup, name='saas_signup'),
    path('login/', user_login, name='saas_login'),
    path('workspaces/', views.workspaces, name='saas_workspaces'),
    path('webhook/razorpay/', views.webhook, name='saas_webhook'),
    path('business/<slug:slug>/', views.business, name='saas_business'),
    path('business/<slug:slug>/settings/', views.branding, name='saas_branding'),
    path('business/<slug:slug>/members/', views.members, name='saas_members'),
    path('business/<slug:slug>/members/<int:pk>/', views.member_action, name='saas_member_action'),
    path('business/<slug:slug>/listings/', views.listings, name='saas_listings'),
    path('business/<slug:slug>/listings/<int:pk>/', views.listing_action, name='saas_listing_action'),
    path('business/<slug:slug>/leads/', views.leads, name='saas_leads'),
    path('business/<slug:slug>/domains/', views.domains, name='saas_domains'),
    path('business/<slug:slug>/domains/<int:pk>/verify/', views.verify_domain, name='saas_verify_domain'),
    path('business/<slug:slug>/checkout/', views.checkout, name='saas_checkout'),
    path('business/<slug:slug>/payment/verify/', views.payment_verify, name='saas_payment_verify'),
]
