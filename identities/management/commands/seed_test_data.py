##seed_test_data.py to create demo test data for application for access control scenarios.
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from identities.models import IdentityProfile, Relationship, DisclosureRule, Context, RelationshipContext

User = get_user_model()

class Command(BaseCommand):
    help = "Seed John/Alice/Charlie test data for access control scenarios."
    def handle(self, *args, **options):
        john, _ = User.objects.get_or_create(username='John', defaults={'email': 'john@example.com'})
        john.set_password('testpass123')
        john.save()

        alice, _ = User.objects.get_or_create(username='Alice', defaults={'email': 'alice@example.com'})
        alice.set_password('testpass123')
        alice.save()

        charlie, _ = User.objects.get_or_create(username='Charlie', defaults={'email': 'charlie@example.com'})
        charlie.set_password('testpass123')
        charlie.save()

        public_ctx, _ = Context.objects.get_or_create(owner=john, name='Public', defaults={'is_public_default': True})
        work_ctx, _ = Context.objects.get_or_create(owner=john, name='Work')
        personal_ctx, _ = Context.objects.get_or_create(owner=john, name='Personal')
        colleague_ctx, _ = Context.objects.get_or_create(owner=john, name='Colleague')
        friend_ctx, _ = Context.objects.get_or_create(owner=john, name='Friend')

        work_identity, _ = IdentityProfile.objects.get_or_create(
            owner=john, context=work_ctx,
            defaults={'identity_name': 'Work Identity',
                        'description': 'Software developer at Blah blah company'}
        )
        personal_identity, _ = IdentityProfile.objects.get_or_create(
            owner=john, context=personal_ctx,
            defaults={'identity_name': 'Chillax bro',
                        'description': 'Likes playing games and chilling with music'}
        )

        rel_charlie, _ = Relationship.objects.get_or_create(owner=john, target_user=charlie)
        RelationshipContext.objects.get_or_create(relationship=rel_charlie, context=colleague_ctx)

        rel_alice, _ = Relationship.objects.get_or_create(owner=john, target_user=alice)
        RelationshipContext.objects.get_or_create(relationship=rel_alice, context=friend_ctx)

        DisclosureRule.objects.get_or_create(identity=work_identity, context=colleague_ctx,
                                                field_name='identity_name', defaults={'is_visible': True})
        DisclosureRule.objects.get_or_create(identity=work_identity, context=colleague_ctx,
                                                field_name='description', defaults={'is_visible': True})
        DisclosureRule.objects.get_or_create(identity=personal_identity, context=friend_ctx,
                                                field_name='description', defaults={'is_visible': True})

        self.stdout.write(self.style.SUCCESS('Test data seeded.'))

