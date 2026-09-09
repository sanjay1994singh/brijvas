"""Isolated local runtime; never connects to the customer's MySQL database."""
from .settings import *

DEBUG = True
SECRET_KEY = 'local-development-only-not-for-production-property-saas'
ALLOWED_HOSTS = ['.localhost', '127.0.0.1', '[::1]', 'testserver', '.example.test']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / '.dev' / 'saas.sqlite3'}}
MEDIA_ROOT = BASE_DIR / '.dev' / 'media'
SAAS_BASE_URL = 'http://localhost:8000'
SAAS_PLATFORM_HOSTS = ['localhost', '127.0.0.1', 'testserver']
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']
