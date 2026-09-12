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
        Create a pending connection request from sender to the user identified
        by recipient_username. Takes a username, not a resolved user object --
        avoids letting a nonexistent user and an undiscoverable user fail
        through different paths; resolving the recipient beforehand would let
        a 404 leak which case it was.
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