## disclosure_service.py file 
from identities.models import DisclosureRule, Context, IdentityProfile, Relationship
## creating a service class to ensure that the business logic for disclosure rules is separated from the views and serializers, making it easier to maintain and test.
class DisclosureService:
    """
    Service layer for disclosure rules and profile visibility. 
    Business logic for disclosure inside here only -- view, and api views and serializer delegate to it than duplicate it. 
    """
    #-- CRUD for DisclosureRule
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

    # -- Visibility / disclosure resolution (from disclosure.py)
    @staticmethod
    def get_effective_contexts(owner, viewer):
        """
        Context tags that apply when 'viewer' looks at 'owner' 's profile.
        Returns None to signal 'owner viewing own profile', no filtering.
        """
        if viewer == owner:
            return None # Own profile, no filtering needed.

        contexts = set()
        public_context = Context.objects.filter(owner=owner, is_public_default=True).first()
        if public_context:
            contexts.add(public_context)

        try:
            relationship = Relationship.objects.get(owner=owner, target_user=viewer)
            contexts |= set(relationship.contexts.all())
        except Relationship.DoesNotExist:
            pass
        return contexts


    @staticmethod
    def get_visible_fields(identity, viewer_contexts):
        """
        Union rule: visible if ANY of the viewer's contexts tag allow it.
        """
        if not viewer_contexts:
            return []
        return list(
            DisclosureRule.objects.filter(
                identity=identity,
                context__in=viewer_contexts, 
                is_visible=True
            ).values_list('field_name', flat=True))


    @staticmethod
    def _resolve_field_values(identity, field_name):
        """
        Resolves a field_name to its actual value -- checks built in IdentityProfile first, then falls back to IdentityAttribute lookup for provider sourced fields (Steam, LinkedIn, etc)
        """
        builtin_keys = {key for key, _ in DisclosureRule.FIELD_CHOICES}
        if field_name in builtin_keys:
            return getattr(identity, field_name, None)
        attributes = identity.attributes.filter(key=field_name).first()
        return attributes.value if attributes else None

    @staticmethod
    def get_visible_identities(owner, viewer):
        """
        Full visible profile payload for other users looking at owner's profile.
        """
        identities = IdentityProfile.objects.filter(owner=owner)
        if owner == viewer:
            results = []
            for identity in identities:
                visible_fields = {f: DisclosureService._resolve_field_values(identity, f) for f, _ in DisclosureRule.FIELD_CHOICES}
                visible_fields.update({attr.key: attr.value for attr in identity.attributes.all()})
                results.append({
                    'identity_id': identity.id,
                    'context_name': identity.context.name,
                    'visible_fields': visible_fields,
                })
            return results
        viewer_contexts = DisclosureService.get_effective_contexts(owner, viewer)
        visible_data = []
        for identity in identities:
            fields = DisclosureService.get_visible_fields(identity, viewer_contexts)
            if fields:
                visible_data.append({
                    'identity_id': identity.id,
                    'context_name': identity.context.name,
                    'visible_fields': {f: DisclosureService._resolve_field_values(identity, f) for f in fields},
                })
        return visible_data