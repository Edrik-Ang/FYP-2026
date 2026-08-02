
## context_service.py file contains the business logic for Context API operations.
## includes methods for retrieving, creating, updating, and deleting contexts, with validation checks to ensure data integrity.
from sqlite3 import IntegrityError

from identities.models import Context
from rest_framework.exceptions import ValidationError

class ContextService:
    @staticmethod
    def get_contexts(user):
        return Context.objects.filter(owner=user)

    @staticmethod
    def create_context(user, serializer):
        try:
            return serializer.save(owner=user)
        except IntegrityError:
            raise ValidationError("You already have a context with this name.")

    @staticmethod
    def update_context(context, serializer):
        if context.is_public_default:
            raise ValidationError("Default public context cannot be renamed.")
        try:
            return serializer.save()
        except IntegrityError:
            raise ValidationError({"name": "You already have a context with this name."})

    @staticmethod
    def delete_context(context):
        if context.is_public_default:
            raise ValidationError("Default public context cannot be deleted.")

        if context.identities.exists():
            raise ValidationError("Context is currently assigned to identities.")

        if context.relationships.exists():
            raise ValidationError("Context is currently assigned to relationships.")

        if context.disclosure_rules.exists():
            raise ValidationError("Context is currently assigned to disclosure rules.")

        context.delete()