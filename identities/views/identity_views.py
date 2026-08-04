## identity_views.py - web facing side for managing identities. 
## Delegates to IdentityService for business rules, same for IdentityListCreateView and IdentityDetailView, so rules are enforced in one place.
from django.contrib import messages
from django.urls import reverse

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from identities.models import IdentityProfile
from identities.serializers import IdentityProfileSerializer
from identities.services.context_service import ContextService
from identities.services.identity_service import IdentityService



@login_required
def identity_list_view(request):
    """
    View to list all identities for the logged-in user.
    """
    identities = IdentityService.list_identities(request.user)
    return render(request, 'identities/identity_list.html', {'identities': identities})


@login_required
def identity_create_view(request):
    """
    View to create a new identity.
    """
    errors = None
    if request.method == 'POST':
        serializer = IdentityProfileSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            IdentityService.create_identity(request.user, serializer)
            return redirect('identity-list')
        errors = serializer.errors
    contexts = ContextService.get_contexts(request.user)
    preselected_context_id = request.GET.get('context')
    if preselected_context_id:
        try:
            preselected_context_id = int(preselected_context_id)
        except (ValueError):
            preselected_context_id = None
    messages.success(request, "Identity created successfully.")
    return render(request, 'identities/identity_form.html', {'errors': errors, 'contexts': contexts, 'preselected_context_id': preselected_context_id})


@login_required
def identity_edit_view(request, pk):
    """
    View to edit an existing identity.
    """
    identity = get_object_or_404(IdentityProfile, pk=pk, owner=request.user)
    errors = None
    if request.method == 'POST':
        serializer = IdentityProfileSerializer(identity, data=request.POST, partial=True, context={'request': request})
        if serializer.is_valid():
            IdentityService.update_identity(serializer)
            return redirect('identity-list')
        errors = serializer.errors
    contexts = ContextService.get_contexts(request.user)
    messages.success(request, "Identity updated successfully.")
    return render(request, 'identities/identity_form.html', {'identity': identity, 'errors': errors, 'contexts': contexts})


@login_required
def identity_delete_view(request, pk):
    """
    View to delete an existing identity.
    """
    identity = get_object_or_404(IdentityProfile, pk=pk, owner=request.user)
    if request.method == 'POST':
        IdentityService.delete_identity(identity)
        messages.success(request, f"Identity '{identity.identity_name}' deleted successfully.")
    return redirect('identity-list')


@login_required
def public_profile_view(request):
    """Dashboard shortcut. Routes to editing the user's exisintg public-context identity if exists, or to create one with public preselected if not. Not a separate model or feature.
    Public is just another context, using existing identity create/edit views."""
    public_identity = IdentityService.get_public_identity(request.user)
    if public_identity:
        return redirect('identity-edit', pk=public_identity.pk)

    public_context = ContextService.get_contexts(request.user).filter(is_public_default=True).first()
    if not public_context:
        messages.error(request, "No public context found. Please create a public context first.")
        return redirect('identity-create')
    return redirect(f"{reverse('identity-create')}?context={public_context.id}")    