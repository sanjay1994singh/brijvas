from .settings_dev import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SAAS_BASE_URL = 'http://localhost'
SAAS_RATE_LIMIT_ENABLED = False
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
