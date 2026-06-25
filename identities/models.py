from django.db import models
from django.conf import settings

##Each identity a user creates will be stored here,
class IdentityProfile(models.Model):
    CONTEXT_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
        ('family', 'Family'),
    ]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, 
                              on_delete=models.CASCADE,
                              related_name='identities') ##Which user owns this identity
    identity_name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    context_category = models.CharField(max_length=20, choices=CONTEXT_CHOICES, default='personal')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.display_name} - {self.identity_name}"


##stores all the relationships between each user
##For the time being, just 3 types: friends, colleagues, family. Will expand later.
class Relationship(models.Model):
    RELATIONSHIP_TYPES = [ ##Will expand to include dynamic relationship types in the future
        ('friend', 'Friend'),
        ('colleague', 'Colleague'),
        ('family', 'Family')
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, 
                              on_delete=models.CASCADE,
                              related_name='relationships') ##Which user owns this relationship
    
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name='related_by') ##Which user is this relationship connecting to
    
    relationship_type = models.CharField(max_length=100,
                                         choices=RELATIONSHIP_TYPES) ##Type of relationship (e.g., friend, colleague)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        unique_together = ('owner', 'target_user')
    def __str__(self):
        return f"{self.owner.username} -> {self.target_user.username} ({self.relationship_type})"

class DisclosureRule(models.Model):
    FIELD_CHOICES = [
        ('identity_name', 'Identity Name'),
        ('display_name', 'Display Name'),
        ('description', 'Description')
    ]
    identity = models.ForeignKey(
        IdentityProfile,
        on_delete=models.CASCADE,
        related_name='disclosure_rules'
    ) ##Which identity does this disclosure rule belong to
    relationship_type = models.CharField(
        max_length=100,
        choices=Relationship.RELATIONSHIP_TYPES
    ) ##Under what relationship type can the Work_identity be disclosed to the identity
    field_name = models.CharField(
        max_length=100,
        choices=FIELD_CHOICES
    ) 
    is_visible = models.BooleanField(default=False) ##Is this field visible to the specified relationship type
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        unique_together = ('identity', 'relationship_type', 'field_name')

    def __str__(self):
        return f"{self.identity.identity_name} visible to {self.relationship_type}"