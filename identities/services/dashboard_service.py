from django.contrib.auth import get_user_model
from identities.models import (IdentityProfile, Relationship, Context)

User = get_user_model()


class DashboardService:
    @staticmethod
    def get_dashboard(user):
        identities = IdentityProfile.objects.filter(owner=user)
        users = User.objects.exclude(id=user.id).order_by('username')
        relationships = Relationship.objects.filter(owner=user).select_related('target_user').prefetch_related("contexts")
        return {
            "me": {"id": user.id, "username": user.username},
            "identities": identities,
            "users": users,
            "relationships": relationships,
            "stats": {
                "identity_count": identities.count(),
                "relationship_count": relationships.count(),
                "context_count": Context.objects.filter(owner=user).count(),
            }
        }