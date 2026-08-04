## disclosure_views.py file -- web facing views for managing disclosure rules.
## delegates business rules to disclosure_service, only one place these rules are enforced.
## identity,Context, field_names are locked on edit (only is_visible can be changed)
## same reasoning as locking target_user on relationship edit: changing the combination isnt an edit instaed is different rule
#  and risks colliding with Disclosure rule's own uniqueness constraints, 
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from ..models import DisclosureRule
from ..serializers import DisclosureRuleSerializer
from ..services.disclosure_service import DisclosureService
from ..services.identity_service import IdentityService
from ..services.context_service import ContextService


@login_required
def disclosure_rule_list_view(request):
    """
    View to list all disclosure rules for the logged-in user.
    """
    rules = DisclosureService.list_rules(request.user)
    return render(request, 'identities/disclosure_rule_list.html', {'rules': rules})


@login_required
def disclosure_rule_create_view(request):
    """
    View to create a new disclosure rule.
    """
    errors = None
    if request.method == 'POST':
        data = request.POST.copy()
        data['is_visible'] = 'is_visible' in request.POST #checkbox only submits if checked, so set to False if not present, not skipped.
        serializer = DisclosureRuleSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            DisclosureService.create_rule(request.user, serializer)
            return redirect('disclosure-rule-list')
        errors = serializer.errors
    identities = IdentityService.list_identities(request.user)
    contexts = ContextService.get_contexts(request.user)
    field_choices = DisclosureRule.FIELD_CHOICES
    return render(request, 'identities/disclosure_rule_form.html', {'errors': errors, 'identities': identities, 'contexts': contexts, 'field_choices': field_choices})


@login_required
def disclosure_rule_edit_view(request, pk):
    """
    View to edit an existing disclosure rule.
    """
    rule = get_object_or_404(DisclosureRule, pk=pk, identity__owner=request.user)
    errors = None
    if request.method == 'POST':
        data = {'is_visible': 'is_visible' in request.POST}  # Only is_visible can be changed
        serializer = DisclosureRuleSerializer(rule, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            DisclosureService.update_rule(serializer)
            return redirect('disclosure-rule-list')
        errors = serializer.errors
    return render(request, 'identities/disclosure_rule_form.html', {'errors': errors, 'rule': rule})


@login_required
def disclosure_rule_delete_view(request,pk):
    """
    View to delete an existing disclosure rule.
    """
    rule = get_object_or_404(DisclosureRule, pk=pk, identity__owner=request.user)
    if request.method == 'POST':
        DisclosureService.delete_rule(rule)
        messages.success(request, 'Disclosure rule deleted successfully.')
    return redirect('disclosure-rule-list')