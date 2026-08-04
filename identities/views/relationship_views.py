## relationship_views.py -- web facing views for managing relationship. 
## Delegates to RelationshipService for business rules, same for RelationshipListCreateView and RelationshipDetailView, so rules are enforced in one place.
## __build_relationship_data forces 'contexts' to always present in the submitted data, even as []. working around HTML's unchecked checkbox omission behavior 
## so serializer' select at least one check reliably fires form the form.
from pyexpat.errors import messages

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators  import login_required
from django.shortcuts import render, redirect, get_object_or_404

from ..disclosure import get_visible_identities

from ..models import Relationship
from ..serializers import RelationshipSerializer
from ..services.relationship_service import RelationshipService
from ..services.context_service import ContextService



User = get_user_model()

def _build_relationship_data(request):
    data = request.POST.copy()
    data.setlist('contexts', request.POST.getlist('contexts'))
    return data

@login_required
def relationship_list_view(request):
    """
    View to list all relationships for the logged-in user.
    """
    relationships = RelationshipService.list_relationships(request.user)
    return render(request, 'identities/relationship_list.html', {'relationships': relationships})

@login_required
def relationship_create_view(request):
    """
    View to create a new relationship.
    """
    errors = None
    if request.method == 'POST':
        data = _build_relationship_data(request)
        serializer = RelationshipSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            RelationshipService.create_relationship(request.user, serializer)
            return redirect('relationship-list')
        errors = serializer.errors
    users = User.objects.exclude(id=request.user.id).order_by('username')
    ## exclude public, matches serializer rules and prevents user from using public context for relationship tagging, meant for public visibility, not relationship tagging
    contexts = ContextService.get_contexts(request.user).exclude(is_public_default=True)
    return render(request, 'identites/relationship_form.html', {'errors': errors, 'users': users, 'contexts': contexts})

@login_required
def relationship_edit_view(request, pk):
    """
    View to edit an existing relationship.
    """
    relationship = get_object_or_404(Relationship, pk=pk, owner=request.user)
    errors = None
    if request.method == 'POST':
        data = _build_relationship_data(request)
        data['target_user'] = relationship.target_user.id ## locked target_user, cannot be changed, only contexts can be changed.
        serializer = RelationshipSerializer(relationship, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            RelationshipService.update_relationship(serializer)
            return redirect('relationship-list')
        errors = serializer.errors
    contexts = ContextService.get_contexts(request.user).exclude(is_public_default=True)
    current_context_ids = set(relationship.contexts.values_list('id', flat=True))
    return render(request, 'identities/relationship_form.html', {'errors': errors, 'relationship': relationship, 'contexts': contexts, 'current_context_ids': current_context_ids})


@login_required
def relationship_delete_view(request, pk):
    """
    View to delete an existing relationship.
    """
    relationship = get_object_or_404(Relationship, pk=pk, owner=request.user)
    if request.method == 'POST':
        RelationshipService.delete_relationship(relationship)
        messages.success(request, f"Relationship with '{relationship.target_user.username}' deleted successfully.")
    return redirect('relationship-list')

@login_required
def relationship_preview_view(request, pk):
    """
    View to preview what the target user of a relationship would see when viewing the current user's profile.
    """
    relationship = get_object_or_404(Relationship, pk=pk, owner=request.user)
    visible_data = get_visible_identities(request.user, relationship.target_user)
    return render(request, 'identities/relationship_preview.html', {'relationship': relationship, 'visible_data': visible_data})
