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

    @staticmethod
    def get_public_identity(user):
        """ Retrieve user's public identity under their own default public context. If any. Ordered by id so repeated calls are deterministic even if user has multiple public identities."""
        return IdentityProfile.objects.filter(owner=user, context__is_public_default=True).select_related('context').order_by('id').first()
    