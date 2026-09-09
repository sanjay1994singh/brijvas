import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from locations.models import State, City
from saas.models import Plan, Tenant
from saas.services import provision


class Command(BaseCommand):
    help = 'Create a local-only demo business and geography without copying customer records.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('Demo setup is allowed only in the isolated SQLite development environment.')
        if Tenant.objects.filter(slug='demo-realty').exists():
            self.stdout.write('Demo workspace already exists; password is unchanged.')
            return
        password = secrets.token_urlsafe(18)
        user = get_user_model().objects.create_user(username='demo-owner', password=password, email='owner@example.test')
        tenant = provision(owner=user, name='Demo Realty', slug='demo-realty', plan=Plan.objects.get(slug='agency'))
        state, _ = State.objects.get_or_create(name='Uttar Pradesh', defaults={'slug': 'uttar-pradesh'})
        City.objects.get_or_create(name='Mathura', state=state, defaults={'slug': 'mathura'})
        self.stdout.write(self.style.SUCCESS(f'Website: {tenant.public_url}\nUsername: demo-owner\nTemporary local password: {password}'))
