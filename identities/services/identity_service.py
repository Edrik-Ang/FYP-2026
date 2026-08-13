## identity_service.py
## handles the business logic for identities, including CRUD operations and validation checks.

from identities.models import IdentityAttribute, IdentityProfile


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

    @staticmethod
    def list_attributes(identity):
        """ List all provider-sourced attributes for an identity."""
        return IdentityAttribute.objects.filter(identity=identity)

    @staticmethod
    def set_attribute(identity, key, value, source=''):
        """ Create or overwrite a attribute on an identity -- 
        used to materialize a selected field from LinkedAccount.raw_data snapshot into something DisclosureRule can refernce by key.
        Overwrite-on-repeat means hitting "refresh" later can safely resync a chosen field without duplicating it. 
        """
        attribute, _ = IdentityAttribute.objects.update_or_create(identity=identity, key=key, defaults={'value': value, 'source': source})
        return attribute

    @staticmethod
    def remove_attribute(identity, key):
        """ Remove a materialized attibute from external provider data. Any DisclosureRule referencing this field_name is left in place but becomes inert
        -- _resolve_field_value returns None for it. Deleting the orphaned rule is a separate, deliberate user action, not an automatic side effect of removing the attribute. 
        """
        IdentityAttribute.objects.filter(identity=identity, key=key).delete()