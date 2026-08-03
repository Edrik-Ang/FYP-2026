## identities/views/context_views.py file handles web-facing views for managing context,
#  Delegates business rules to ContextService, only one place these rules are enforced.

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.exceptions import ValidationError

from ..models import Context
from ..serializers import ContextSerializer
from identities.services.context_service import ContextService


def _errors_from_validation_error(exc):
    """
    Helper function: Normalise DRF validationerror's detail' into the same {field: [messages]} shape serializers.errors ueses, 
    This way template's error rendering loop works same regardlewss of source."""
    detail = exc.detail
    if isinstance(detail, dict):
        return {field: value if isinstance(value, list) else [value] for field, value in detail.items()}
    if isinstance(detail, list):
        return {'non_field_errors': detail}
    return {'non_field_errors': [detail]}

@login_required
def context_list_view(request):
    contexts = ContextService.get_contexts(request.user)
    return render(request, 'identtities/context_list.html', {'contexts': contexts})


@login_required
def context_list_view(request):
    contexts = ContextService.get_contexts(request.user)
    return render(request, 'identities/context_list.html', {'contexts': contexts})


@login_required
def context_create_view(request):
    errors = None
    if request.method == 'POST':
        serializer = ContextSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            try:
                ContextService.create_context(request.user, serializer)
                return redirect('context-list')
            except ValidationError as e:
                errors = _errors_from_validation_error(e)
        else:
            errors = serializer.errors
    return render(request, 'identities/context_form.html', {'errors': errors})


@login_required
def context_edit_view(request, pk):
    context = get_object_or_404(Context, pk=pk, owner=request.user)
    errors = None
    if request.method == 'POST':
        serializer = ContextSerializer(context, data=request.POST, partial=True, context={'request': request})
        if serializer.is_valid():
            try:
                ContextService.update_context(context, serializer)
                return redirect('context-list')
            except ValidationError as e:
                errors = _errors_from_validation_error(e)
        else:
            errors = serializer.errors
    return render(request, 'identities/context_form.html', {'context': context, 'errors': errors})


@login_required
def context_delete_view(request, pk):
    context = get_object_or_404(Context, pk=pk, owner=request.user)
    if request.method == 'POST':
        try:
            ContextService.delete_context(context)
            messages.success(request, f"Context '{context.name}' deleted successfully.")
        except ValidationError as e:
            first_message = next(iter(_errors_from_validation_error(e).values()))[0]
            messages.error(request, str(first_message))
    return redirect('context-list')