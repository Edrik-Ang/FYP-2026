# Models.py for identities app. 
# Defines the models for the database tables for the identities app.

from django.db import models
from django.conf import settings

## Context class encompasses user-defined labels, e.g employers, Cafe-friends, Colleagues, etc
## user use these labels to categorize their own IdentityProfiles and to tag relationships with other users.
class Context(models.Model):
    """
    A user-defined label, e.g 'colleagues', 'cafe-friends', 'gamers', 'classmates'.
    Used to categorise owner's own IdentityProfiles AND to tag 
    relationships with other users -- same vocabulary, both places.
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contexts')
    name = models.CharField(max_length=100)
    is_public_default = models.BooleanField(default=False) ##For default public profile for discoverability
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return f"{self.owner.username}: {self.name}"

##Each identity a user creates will be stored here,
class IdentityProfile(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='identities') ##Which user owns this identity
    context = models.ForeignKey(Context, on_delete=models.CASCADE, related_name='identities') ##Which context does this identity belong to
    identity_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.owner.username}: {self.identity_name}"

##stores all the relationships between each user
##For the time being, just 3 types: friends, colleagues, family. Will expand later.
class Relationship(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='relationships')
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='related_by') ##Which user is this relationship connecting to
    contexts = models.ManyToManyField(Context, through='RelationshipContext', related_name='relationships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        unique_together = ('owner', 'target_user') ## still one edge per pair, just multiple context tags per edge

    def __str__(self):
        return f"{self.owner.username} -> {self.target_user.username}"

## RelationshipContext is a through model that connects a Relationship to a Context, allowing for multiple contexts to be associated with a single relationship. 
# This enables users to categorize their relationships with other users using the same vocabulary they use for their own IdentityProfiles.
class RelationshipContext(models.Model):
    relationship = models.ForeignKey(Relationship, on_delete=models.CASCADE)
    context = models.ForeignKey(Context, on_delete=models.CASCADE)
    tagged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('relationship', 'context')

    def __str__(self):
        return f"{self.relationship.owner.username} -> {self.relationship.target_user.username} in context {self.context.name}"


class DisclosureRule(models.Model):
    FIELD_CHOICES = [ ## Built-in identity fields. No longer enforced via choices=  -- 
                      ## IdentityAttribute keys are equally valid field_names now, validated dynamically in DisclosureService.
        ('identity_name', 'Identity Name'),
        ('description', 'Description') 
    ]
    identity = models.ForeignKey(IdentityProfile, on_delete=models.CASCADE,related_name='disclosure_rules') ##Which identity does this disclosure rule belong to
    context = models.ForeignKey(Context, on_delete=models.CASCADE, related_name='disclosure_rules') ##Which context does this disclosure rule belong to
    field_name = models.CharField(max_length=100) ## was choices=FIELD_CHOICES 
    is_visible = models.BooleanField(default=False) ##Is this field visible to the specified context
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        unique_together = ('identity', 'context', 'field_name')

    def __str__(self):
        return f"{self.identity.owner.username} {self.identity.identity_name} 's {self.field_name} visible to {self.context}"

    def get_field_name_display(self):## meant to replace django's auto-gen display method, only exists when 'choices' is defined, falls back to field_name if not found in choices. 
        return dict(self.FIELD_CHOICES).get(self.field_name, self.field_name)
    
## Used to store various attributes of an identity (Future work)
## Steam has recent games, comments, Linkedin has work experience, about card, etc
# Allows for flexibility in the types of information that can be associated with an identity, enabling users to customize their profiles based on their needs and preferences. 
class IdentityAttribute(models.Model):
    identity = models.ForeignKey(IdentityProfile, on_delete=models.CASCADE, related_name='attributes')
    key = models.CharField(max_length=100) ## 'recent activity', 'experience', 'education', ... 
    value = models.JSONField() ## store string, list of dicts, whatever the platform from Steam and LinkedIN API provides.
    source = models.CharField(max_length=50, blank=True) ## Steam, LinkedIn, others
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('identity', 'key') # one value per key per identity

    def __str__(self):
        return f"{self.identity.identity_name} - {self.key}: ({self.source})"

## Used to store linked external accounts for a user, such as Steam, LinkedIn, Reddit, etc.
class LinkedAccount(models.Model):
    """
    Links external identtiy provider account (e.g Steam, LinkedIn, Reddit...) to a user 
    One row per (user, provide) -- relinking overwrites provider_uid than creating a new separate row. 
    Provider_uid is globally unique per provider, so same external account cant be claimed by multiple users. 
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='linked_accounts')
    provider = models.CharField(max_length=32) # e.g 'steam', 'linkedin', 'reddit'
    provider_uid = models.CharField(max_length=255) # SteamID64, etc
    access_token = models.CharField(max_length=512, blank=True, null=True) # Not used for Steam
    refresh_token = models.CharField(max_length=512, blank=True, null=True) # Not used for Steam
    token_expires_at = models.DateTimeField(blank=True, null=True) # Not used for Steam

    raw_data = models.JSONField(default=dict, blank=True)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['provider', 'provider_uid'], name='unique_provider_uid'),
            models.UniqueConstraint(fields=['user', 'provider'], name='unique_user_provider')
        ]

    def __str__(self):
        return f"{self.user.username}: {self.provider} ({self.provider_uid})"
