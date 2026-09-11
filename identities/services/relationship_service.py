## relationship_service.py handles the business logic for managing relationships, including listing, creating, updating, and deleting relationships.
## All validation inside RelationshipSerializer
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
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