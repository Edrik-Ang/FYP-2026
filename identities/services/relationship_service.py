## relationship_service.py handles the business logic for managing relationships, including listing, creating, updating, and deleting relationships.
## All validation inside RelationshipSerializer
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from identities.models import Relationship, ConnectionRequest, UserProfile

User = get_user_model()
RESEND_COOLDOWN = timedelta(hours=1)

class RelationshipService:

    @staticmethod
    def list_relationships(user):
        """
        List relationships for a specific user.
        """
        return Relationship.objects.filter(owner=user).select_related("target_user").prefetch_related("contexts").order_by("target_user__username")

    @staticmethod
    def create_relationship(user, serializer):
        """
        Create a new relationship for a specific user.
        """
        return serializer.save(owner=user)

    @staticmethod
    def update_relationship(serializer):
        """
        Update an existing relationship.
        """
        return serializer.save()

    @staticmethod
    def delete_relationship(relationship):
        """
        Delete an existing relationship.
        """
        relationship.delete()

    @staticmethod
    def create_request(sender, recipient_username):
        """
        Create or revivie a connection request from sender to user identified by recipient_username. 
        At most one connectionRequuest row exists per directed pair, a resend after decline (past cooldown) updates same row, than pending rahter than creating a new one.
        """
        try:
            recipient = User.objects.select_related('profile').get(username=recipient_username)
            if not recipient.profile.is_discoverable:
                raise ValidationError("Unable to send connection request.")
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            raise ValidationError("Unable to send connection request.")

        if recipient == sender:
            raise ValidationError("Unable to send connection request.")

        existing = ConnectionRequest.objects.filter(sender=sender, recipient=recipient).first()
        if existing:
            if existing.status == ConnectionRequest.PENDING:
                raise ValidationError("You already have a pending request to this user.")
            if existing.status == ConnectionRequest.ACCEPTED:
                raise ValidationError("You are already connected to this user.")
            if existing.status == ConnectionRequest.DECLINED:
                if existing.responded_at and existing.responded_at > timezone.now() - RESEND_COOLDOWN:
                    raise ValidationError("You cannot send a new connection request to this user yet. Please wait before trying again.")

                existing.status = ConnectionRequest.PENDING
                existing.responded_at = None
                existing.save()
                return existing

        return ConnectionRequest.objects.create(sender=sender, recipient=recipient)


    @staticmethod
    def accept_request(connection_request, actor):
        """ Accepts a pending connection request, (something like friend request) actor is recipient.
            the view is expected to have already scoped the fetch to recipient=request.user, but this check stays regardless,
            so method is safe to call from anywhere without relying on the caller having scoped the query correctly.
        """
        if connection_request.recipient != actor:
            raise ValidationError("You are not authorized to respond to this request")
        if connection_request.status != ConnectionRequest.PENDING:
            raise ValidationError("This request has already been responded to.")
        connection_request.status = ConnectionRequest.ACCEPTED
        connection_request.responded_at = timezone.now()
        connection_request.save()
        return connection_request


    @staticmethod
    def decline_request(connection_request, actor):
        """ Declines a pending connection request, (similar to like rejecting a friend request). saem ownership/status checks as accept_request.
            Declining a starts the resend cooldown (see create_request()'s check against the most recent DECLINED row.)
        """
        if connection_request.recipient != actor:
            raise ValidationError("You are not authorized to respond to this request.")
        if connection_request.status != ConnectionRequest.PENDING:
            raise ValidationError("This request has already been responded to.")
        connection_request.status = ConnectionRequest.DECLINED
        connection_request.responded_at = timezone.now()
        connection_request.save()
        return connection_request


    @staticmethod
    def get_connected_user_ids(user):
        """ Returns a set of user IDs with an ACCEPTED CONNECTION_REQUEST with 'user', in either direct, Shared by RelationshipSerializer's creation gate
         and relationship_create_view dropdown, so both stay synced. """
        accepted_pairs = ConnectionRequest.objects.filter(
            Q(sender=user) | Q(recipient=user), status=ConnectionRequest.ACCEPTED,
        ).values_list('sender_id', 'recipient_id')
        return {uid for pair in accepted_pairs for uid in pair if uid != user.id}


    @staticmethod
    def get_connection_overview(user):
        """ Returns a list of connection overview data for the given user. """
        requests = ConnectionRequest.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).select_related('sender', 'recipient')

        other_users = {}
        for req in requests:
            other = req.recipient if req.sender_id == user.id else req.sender
            other_users[other.id] = other

        overview = []
        for other in other_users.values():
            status = RelationshipService.get_connection_status(user, other)
            overview.append({'other_user': other, **status})

        overview.sort(key=lambda item: item['other_user'].username)
        return overview

    @staticmethod
    def get_connection_status(viewer, other_user):
        """ Read only status lookup drives the connect button on a profile page,
        viewer will always see the correct statte based on what would acutally happen if they click the button. """
        if viewer == other_user:
            return {'state': 'self'}

        accepted = ConnectionRequest.objects.filter(
            Q(sender=viewer, recipient=other_user) | Q(sender=other_user, recipient=viewer),
            status=ConnectionRequest.ACCEPTED,
        ).exists()
        if accepted:
            relationship = Relationship.objects.filter(owner=viewer, target_user=other_user).first()
            return {
                'state': 'connected',
                'relationship_id': relationship.id if relationship else None,
            }

        outgoing_pending = ConnectionRequest.objects.filter(
            sender=viewer, recipient=other_user, status=ConnectionRequest.PENDING
        ).exists()
        if outgoing_pending:
            return {'state': 'pending_outgoing'}
        
        incoming = ConnectionRequest.objects.filter(
            sender=other_user, recipient=viewer, status=ConnectionRequest.PENDING
        ).first()
        if incoming:
            return {'state': 'pending_incoming', 'request_id': incoming.pk}
        
        last_declined = ConnectionRequest.objects.filter(
            sender=viewer, recipient=other_user, status=ConnectionRequest.DECLINED,
        ).first()
        if last_declined and last_declined.responded_at and last_declined.responded_at > timezone.now() - RESEND_COOLDOWN:
            return {'state': 'cooldown'}

        return {'state': 'none'}