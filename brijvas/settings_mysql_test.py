"""Server-local MySQL test database; run as a database test operator, never as app service."""
from .settings_test import *

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'brijvas_saas_stage',
    'USER': os.getenv('SAAS_TEST_DB_USER', 'root'),
    'PASSWORD': os.getenv('SAAS_TEST_DB_PASSWORD', ''),
    'HOST': os.getenv('SAAS_TEST_DB_HOST', ''),
    'TEST': {'NAME': 'test_brijvas_saas'},
    'OPTIONS': {'charset': 'utf8mb4'},
}}
