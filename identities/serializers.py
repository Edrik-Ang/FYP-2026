## serializers.py file
## handles serialization and deserialization of data for the identities app
## converts complex data types like model instances into native Python datatypes that can then be easily rendered into JSON, XML or other content types.
from django.contrib.auth import get_user_model
from .models import Context, IdentityProfile, Relationship, DisclosureRule
from rest_framework import serializers

User = get_user_model()

## Serializer for registering new users, including username, email, and password fields. Password is write-only for security.
## Handles converting User instances to and from JSON, and creating new users (Password encryption is handled by Django's built-in create_user method).
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Context.objects.create(owner=user, name='Public', is_public_default=True)  ## create default public context for new user
        return user

##Serializer for Context model, handles converting Context instances to and from JSON
class ContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Context
        fields = ['id', 'name', 'is_public_default', 'created_at']
        read_only_fields = ['id', 'is_public_default', 'created_at']

## Serializer for IdentityProfile model, handles converting IdentityProfile instances to and from JSON
## Includes context_name field for convenience, which is read-only and derived from the related Context model.
class IdentityProfileSerializer(serializers.ModelSerializer):
    context_name = serializers.CharField(source='context.name', read_only=True)
    
    class Meta:
        model = IdentityProfile
        fields = ['id', 'identity_name', 'description', 'context', 'context_name', 'created_at']
        read_only_fields = ['id', 'created_at'] ## context is writable so owners can reassign which context each identity belongs to
        ## context_name is read-only, just for convenience.
    
    ##validate owner of context when creating identity, otherwise a user can assign their identity to someone else's context, which is not allowed.
    def validate_context(self, value):
        request = self.context.get('request')
        if request and value.owner != request.user:
            raise serializers.ValidationError("You can only assign your own contexts to your identities.")
        return value

##Serializes the relationship model 
## handles converting Relationship instances to and from JSON, including the target user's username and the contexts associated with the relationship.
class RelationshipSerializer(serializers.ModelSerializer):
    target_username = serializers.CharField(source='target_user.username', read_only=True)
    contexts = serializers.PrimaryKeyRelatedField(many=True, queryset=Context.objects.all())

    class Meta:
        model = Relationship
        fields = [
            'id' , 'target_user', 'target_username','contexts', 'created_at']
        read_only_fields = ['id', 'created_at'] #exclude owner from writable fields, as it should be set automatically to the authenticated user making the request.
    
    ##when user create new relationship, specify target_user and contexts, owner is automatically set to the authenticated user making the request.
    def create(self, validated_data):
        contexts = validated_data.pop('contexts', [])
        relationship = Relationship.objects.create(**validated_data)
        relationship.contexts.set(contexts)
        return relationship
    
    ## user updates relationship, can change contexts, instead of creating new relationship, just update the contexts of existing relationship.
    def update(self, instance, validated_data):
        contexts = validated_data.pop('contexts', None)
        instance = super().update(instance, validated_data)
        if contexts is not None:
            instance.contexts.set(contexts)
        return instance
    
    ## validate that user only tags relationships with their own contexts, 
    ## Ensures users only create relationships with other users and not themselves, preventing self-referential relationships.
    def validate(self, attrs):
        request = self.context.get('request')
        contexts = attrs.get('contexts')
        target_user = attrs.get('target_user', getattr(self.instance, 'target_user', None))
        
        if request and contexts:
            for context in contexts:
                if context.owner != request.user:
                    raise serializers.ValidationError(f"You can only tag relationships with your own contexts.")

        if request and target_user == request.user:
            raise serializers.ValidationError("You cannot create a relationship with yourself.")
        
        return attrs

## Serializer for DisclosureRule model, handles converting DisclosureRule instances to and from JSON
## handles validation to ensure that users can only create disclosure rules for their own identities and contexts, preventing unauthorized access or modifications.
class DisclosureRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisclosureRule
        fields = ['id', 'identity', 'context', 'field_name','is_visible', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        ## disclosureRules no direct owner field -- ownership from identity's owner and context's owner
        ## Without checking, user can attach rule to someone else's identity or context
        request = self.context.get('request')
        identity = attrs.get('identity', getattr(self.instance, 'identity', None))
        context = attrs.get('context', getattr(self.instance, 'context', None))
        
        if request and identity.owner != request.user:
            raise serializers.ValidationError("You can only set disclosure rules for your own identities.")
        
        if request and context.owner != request.user:
            raise serializers.ValidationError("You can only use your own contexts for disclosure rules.")
        return attrs

## for disclosure/viewing endpoint purposes
class VisibleIdentitySerializer(serializers.Serializer):
    identity_id = serializers.IntegerField()
    context_name = serializers.CharField()
    visible_fields = serializers.DictField()

## used for searching users by username, returns id and username of matching users
class UserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']



## Other serializers later (Steam , LinkedIn)