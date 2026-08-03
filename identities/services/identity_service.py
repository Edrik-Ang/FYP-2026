## identity_service.py
## handles the business logic for identities, including CRUD operations and validation checks.

from identities.models import IdentityProfile


class IdentityService:
    """
    IdentityService handles the business logic related to identites, Includes the CRUD operations and validation checks
    Used by both API and web views to ensure consistent business rules.
    """

    @staticmethod
    def list_identities(user):
        """
        List identities for a specific user.
        """
        return (IdentityProfile.objects.filter(owner=user).select_related('owner','context').order_by('identity_name'))

    @staticmethod
    def create_identity(user, serializer):
        """
        Create a new identity for a specific user.
        """
        return serializer.save(owner=user)

    @staticmethod
    def update_identity(serializer):
        """
        Update an existing identity.
        """
        return serializer.save()

    @staticmethod
    def delete_identity(identity):
        """
        Delete an existing identity.
        """
        identity.delete()
