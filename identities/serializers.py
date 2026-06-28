from django.contrib.auth import get_user_model
from .models import IdentityProfile, Relationship, DisclosureRule
from rest_framework import serializers

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class IdentityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityProfile
        fields = [
            'id', 'identity_name', 'display_name',
            'description', 'context_cateogry', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

##Serializes the relationship model 
class RelationshipSerializer(serializers.ModelSerializer):
    target_username = serializers.CharField(source='target_user.username',
                                            read_only=True
                                            )
    class Meta:
        model = Relationship
        fields = [
            'id', 'owner', 'target_user', 'target_username',
            'relationship_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class DisclosureRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisclosureRule
        fields = [
            'id', 'identity', 'relationship_type', 'field_name',
            'is_visible', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
