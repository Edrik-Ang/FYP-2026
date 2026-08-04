## relationship_service.py handles the business logic for managing relationships, including listing, creating, updating, and deleting relationships.
## All validation inside RelationshipSerializer
from identities.models import Relationship

class RelationshipService:

    @staticmethod
    def list_relationships(user):
        """
        List relationships for a specific user.
        """
        return Relationship.objects.filter(owner=user).select_related("target_user").prefetch_related("contexts").order_by("target_user__username")

    @staticmethod
    def create_relationship(user, serializer):
        """
        Create a new relationship for a specific user.
        """
        return serializer.save(owner=user)

    @staticmethod
    def update_relationship(serializer):
        """
        Update an existing relationship.
        """
        return serializer.save()

    @staticmethod
    def delete_relationship(relationship):
        """
        Delete an existing relationship.
        """
        relationship.delete()