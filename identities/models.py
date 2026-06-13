from django.db import models
from django.conf import settings

##Each identity a user creates will be stored here,
class IdentityProfile(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, 
                              on_delete=models.CASCADE,
                              related_name='identities') ##Which user owns this identity
    identity_name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
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
    def __str__(self):
        return f"{self.owner.username} -> {self.target_user.username} ({self.relationship_type})"

class DisclosureRule(models.Model):
    identity = models.ForeignKey(IdentityProfile, on_delete=models.CASCADE, related_name='disclosure_rules') ##Which identity does this disclosure rule belong to
    relationship_type = models.CharField(max_length=100, choices=Relationship.RELATIONSHIP_TYPES) ##Under what relationship type can the Work_identity be disclosed to the identity
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.identity.identity_name} visible to {self.relationship_type}"