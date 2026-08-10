from django.contrib.auth import get_user_model
from identities.models import (IdentityProfile, LinkedAccount, Relationship, Context)

User = get_user_model()


class DashboardService:
    @staticmethod
    def get_dashboard(user):
        identities = IdentityProfile.objects.filter(owner=user)
        users = User.objects.exclude(id=user.id).order_by('username')
        relationships = Relationship.objects.filter(owner=user).select_related('target_user').prefetch_related("contexts")
        contexts = Context.objects.filter(owner=user)
        linked_accounts = {account.provider: account for account in LinkedAccount.objects.filter(user=user)}
        return {
            "me": {"id": user.id, "username": user.username},
            "identities": identities,
            "users": users,
            "relationships": relationships,
            "contexts": contexts,
            "linked_accounts": linked_accounts,
            "stats": {
                "identity_count": identities.count(),
                "relationship_count": relationships.count(),
                "context_count": Context.objects.filter(owner=user).count(),
            }
        }