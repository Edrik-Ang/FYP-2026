## seed_test_data.py — demo data for access-control scenarios across 4 users.
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from identities.models import IdentityProfile, Relationship, DisclosureRule, Context, RelationshipContext

User = get_user_model()

# Short, unique-enough bios per user/identity — no real people, generic roles.
IDENTITY_DESCRIPTIONS = {
    'John': {
        'Work': 'Backend developer building internal tools at a logistics startup.',
        'Personal': 'Into board games, weekend hikes, and terrible puns.',
    },
    'Alice': {
        'Work': 'Marketing coordinator running social campaigns for a retail brand.',
        'Personal': 'Amateur baker, currently obsessed with getting sourdough right.',
    },
    'Bob': {
        'Work': 'Warehouse operations supervisor overseeing the night shift.',
        'Personal': 'Plays bass in a garage band and collects vinyl records.',
    },
    'Charlie': {
        'Work': 'Junior data analyst learning SQL and building dashboards.',
        'Personal': 'Trains for half-marathons and volunteers at the animal shelter.',
    },
}

# owner_username -> target_username -> context names tagging that relationship.
# John->Alice and Alice->Bob each carry two tags on purpose, to exercise the
# union rule: a second tag should ADD visibility, never take it away.
RELATIONSHIPS = {
    'John': {
        'Charlie': ['Colleague'],
        'Alice': ['Friend', 'Colleague'],
        'Bob': ['Family'],
    },
    'Alice': {
        'John': ['Friend'],
        'Bob': ['Colleague', 'Family'],
    },
    'Bob': {
        'John': ['Family'],
        'Charlie': ['Friend'],
    },
    'Charlie': {
        'John': ['Colleague'],
    },
}

CONTEXT_NAMES = ['Work', 'Personal', 'Family', 'Friend', 'Colleague']


class Command(BaseCommand):
    help = "Seed John/Alice/Bob/Charlie test data covering multi-context relationships and access-control scenarios."

    def handle(self, *args, **options):
        users = {}
        contexts = {}     # (username, context_name) -> Context
        identities = {}   # (username, context_name) -> IdentityProfile

        for username in IDENTITY_DESCRIPTIONS:
            user, _ = User.objects.get_or_create(
                username=username, defaults={'email': f'{username.lower()}@example.com'}
            )
            user.set_password('testpass123')
            user.save()
            users[username] = user

            # Fetched by the is_public_default flag rather than by name, so
            # this stays correct whether or not a registration signal already
            # created a default context for this user under a different name.
            public_ctx, _ = Context.objects.get_or_create(
                owner=user, is_public_default=True, defaults={'name': 'Public'}
            )
            contexts[(username, 'Public')] = public_ctx

            for context_name in CONTEXT_NAMES:
                ctx, _ = Context.objects.get_or_create(owner=user, name=context_name)
                contexts[(username, context_name)] = ctx

            for context_name in ('Work', 'Personal'):
                identity, _ = IdentityProfile.objects.get_or_create(
                    owner=user,
                    context=contexts[(username, context_name)],
                    defaults={
                        'identity_name': f'{context_name} Identity',
                        'description': IDENTITY_DESCRIPTIONS[username][context_name],
                    },
                )
                identities[(username, context_name)] = identity

        for owner_name, targets in RELATIONSHIPS.items():
            owner = users[owner_name]
            for target_name, context_names in targets.items():
                target = users[target_name]
                relationship, _ = Relationship.objects.get_or_create(owner=owner, target_user=target)
                for context_name in context_names:
                    RelationshipContext.objects.get_or_create(
                        relationship=relationship,
                        context=contexts[(owner_name, context_name)],
                    )

        for username in IDENTITY_DESCRIPTIONS:
            work_identity = identities[(username, 'Work')]
            personal_identity = identities[(username, 'Personal')]
            colleague_ctx = contexts[(username, 'Colleague')]
            friend_ctx = contexts[(username, 'Friend')]
            family_ctx = contexts[(username, 'Family')]

            DisclosureRule.objects.get_or_create(
                identity=work_identity, context=colleague_ctx,
                field_name='identity_name', defaults={'is_visible': True},
            )
            DisclosureRule.objects.get_or_create(
                identity=work_identity, context=colleague_ctx,
                field_name='description', defaults={'is_visible': True},
            )
            DisclosureRule.objects.get_or_create(
                identity=personal_identity, context=friend_ctx,
                field_name='description', defaults={'is_visible': True},
            )
            DisclosureRule.objects.get_or_create(
                identity=personal_identity, context=family_ctx,
                field_name='identity_name', defaults={'is_visible': True},
            )
            DisclosureRule.objects.get_or_create(
                identity=personal_identity, context=family_ctx,
                field_name='description', defaults={'is_visible': True},
            )

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(users)} users, {len(contexts)} contexts, '
            f'{len(identities)} identities, and relationships across the group.'
        ))