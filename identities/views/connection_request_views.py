# identities/views/connection_request_views.py -- web-facing views for connection requests.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.exceptions import ValidationError

from ..models import ConnectionRequest
from ..services.relationship_service import RelationshipService


@login_required
def connection_request_list_view(request):
    incoming = ConnectionRequest.objects.filter(
        recipient=request.user, status=ConnectionRequest.PENDING
    ).select_related('sender').order_by('-created_at')
    outgoing = ConnectionRequest.objects.filter(
        sender=request.user
    ).select_related('recipient').order_by('-created_at')
    return render(request, 'identities/connection_request_list.html', {
        'incoming': incoming, 'outgoing': outgoing,
    })


@login_required
def connection_request_create_view(request):
    error = None
    if request.method == 'POST':
        recipient_username = request.POST.get('recipient_username', '').strip()
        try:
            RelationshipService.create_request(request.user, recipient_username)
            messages.success(request, f"Connection request sent to '{recipient_username}'.")
            return redirect('connection-request-list')
        except ValidationError as e:
            error = e.detail[0] if isinstance(e.detail, list) else e.detail
    return render(request, 'identities/connection_request_form.html', {'error': error})


@login_required
def connection_request_accept_view(request, pk):
    connection_request = get_object_or_404(ConnectionRequest, pk=pk, recipient=request.user)
    if request.method == 'POST':
        RelationshipService.accept_request(connection_request, request.user)
        messages.success(request, f"Connection with '{connection_request.sender.username}' accepted.")
    return redirect('connection-request-list')


@login_required
def connection_request_decline_view(request, pk):
    connection_request = get_object_or_404(ConnectionRequest, pk=pk, recipient=request.user)
    if request.method == 'POST':
        RelationshipService.decline_request(connection_request, request.user)
        messages.success(request, f"Connection request from '{connection_request.sender.username}' declined.")
    return redirect('connection-request-list')