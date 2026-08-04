## Disclosure.py file  
# view functions and logic for Disclosure rules

##Disclosure functions
## get_effective_contexts function used for filtering contexts tags for a given owner and viewer.
## Takes in owner and viewer as params, returns None if owner and viewer are the same, 
## else returns a list of contexts that apply when viewer looks at owner's profile.
from .models import Context, Relationship, DisclosureRule, IdentityProfile

def get_effective_contexts(owner, viewer):
    """
    Context tags that apply when viewer looks at `owner`'s profile. 
    Returns None to signal 'owner viewing own profile', no filtering'.
    """
    if viewer == owner:
        return None # Own profile, no filtering needed

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

## get_visible_fields function used for getting visble fields based on viewer's context and identity
## If any of viewer tag allow it, it will be visible.
def get_visible_fields(identity, viewer_contexts):
    """
    Union rule: visible if ANY of the viewer's context tags allow it.
    """
    if not viewer_contexts:
        return []
    return list(
        DisclosureRule.objects.filter(
            identity=identity, context__in=viewer_contexts, is_visible=True
        ).values_list('field_name', flat=True)
    )

# get_visible_identities function used for getting visible identities based on owner and viewer
def get_visible_identities(owner, viewer):
    identities = IdentityProfile.objects.filter(owner=owner)

    if owner == viewer:
        return [
            {
                'identity_id': identity.id,
                'context_name': identity.context.name,
                'visible_fields': {f: getattr(identity, f) for f, _ in DisclosureRule.FIELD_CHOICES},
            }
            for identity in identities
        ]

    viewer_contexts = get_effective_contexts(owner, viewer)
    visible_data = []
    for identity in identities:
        fields = get_visible_fields(identity, viewer_contexts)
        if fields:
            visible_data.append({
                'identity_id': identity.id,
                'context_name': identity.context.name,
                'visible_fields': {f: getattr(identity, f) for f in fields},
            })
    return visible_data

## get visible attributes

## build public profile 

