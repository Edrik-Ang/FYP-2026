## disclosure_service.py file 
from identities.models import DisclosureRule
## creating a service class to ensure that the business logic for disclosure rules is separated from the views and serializers, making it easier to maintain and test.
class DisclosureService:

    @staticmethod
    def list_rules(user):
        """
        List disclosure rules for a specific user.
        """
        return (DisclosureRule.objects.filter(identity__owner=user).select_related("identity","context").order_by("identity__identity_name","context__name"))

    @staticmethod
    def create_rule(user, serializer):
        """
        Create a new disclosure rule for a specific user.
        """
        return serializer.save()

    @staticmethod
    def update_rule(serializer):
        """
        Update an existing disclosure rule.
        """
        return serializer.save()

    @staticmethod
    def delete_rule(rule):
        """
        Delete an existing disclosure rule.
        """
        rule.delete()