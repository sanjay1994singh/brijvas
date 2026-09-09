from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from saas.models import Tenant, Membership, AuditEvent


class Command(BaseCommand):
    help = 'Assign an existing account as owner of a migrated business without changing platform permissions.'

    def add_arguments(self, parser):
        parser.add_argument('slug')
        parser.add_argument('username')

    @transaction.atomic
    def handle(self, *args, **options):
        tenant = Tenant.objects.select_for_update().filter(slug=options['slug']).first()
        user = get_user_model().objects.filter(username=options['username'], is_active=True).first()
        if not tenant or not user:
            raise CommandError('Business and active account must already exist.')
        if tenant.owner_id and tenant.owner_id != user.pk:
            raise CommandError('Business already has a different owner. Ownership transfer requires a separate reviewed procedure.')
        tenant.owner = user
        tenant.save(update_fields=['owner'])
        Membership.objects.update_or_create(tenant=tenant, user=user, defaults={'role': 'owner', 'is_active': True, 'is_approved': True})
        AuditEvent.objects.create(tenant=tenant, actor=user, action='owner.assigned')
        self.stdout.write(self.style.SUCCESS('Business owner assigned.'))
