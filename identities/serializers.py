## serializers.py file
## handles serialization and deserialization of data for the identities app
## converts complex data types like model instances into native Python datatypes that can then be easily rendered into JSON, XML or other content types.
import re
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import ConnectionRequest, Context, IdentityProfile, LinkedAccount, Relationship, DisclosureRule
from rest_framework import serializers
from rest_framework.validators import UniqueValidator 

User = get_user_model()

## Serializer for registering new users, including username, email, and password fields. Password is write-only for security.
## Handles converting User instances to and from JSON, and creating new users (Password encryption is handled by Django's built-in create_user method).
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=20)
    password2 = serializers.CharField(write_only=True, max_length=20, label="Confirm Password")
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="This email is already in use.")]) 

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate_password(self,value):
        ## Runs AUTH_PASSWORD_VALIDATORS from settings.py to ensure password meets security requirements
        ## MinimumLengthValidator default is 8, and similarity/common-password/all-numeric checks.
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        # custom regex validation (mix of letters and digits
        if not re.search(r'[A-Za-z]', value) or not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one letter and one digit.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')  ## remove password2 as it's not needed for user creation
        user = User.objects.create_user(**validated_data)
        return user


## Serializer for login, validates username and password fields, no need modelSerializer as login dont create/update a user instance, 
## just validates credentials and returns a token if valid.
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, trim_whitespace=False)
    password = serializers.CharField(required=True, trim_whitespace=False, write_only=True)


##Serializer for Context model, handles converting Context instances to and from JSON
class ContextSerializer(serializers.ModelSerializer):


    class Meta:
        model = Context
        fields = ['id', 'name', 'is_system', 'created_at']
        read_only_fields = ['id', 'is_system', 'created_at']

    def validate_name(self, value):
        request = self.context['request']
        exists = Context.objects.filter(owner=request.user, name=value)

        if self.instance:
            exists = exists.exclude(pk=self.instance.pk)

        if exists.exists():
            raise serializers.ValidationError("You already have a context with this name.")
        
        return value


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

    ## Validation logic ensure user cannot have many identities with same name in same context, but can have same identity_name in different contexts.
    def validate(self, attrs):
        request = self.context['request']
        context = attrs.get("context", getattr(self.instance, "context", None))
        identity_name = attrs.get("identity_name", getattr(self.instance, "identity_name", None))
        exists = IdentityProfile.objects.filter(owner=request.user, context=context, identity_name=identity_name)
        if self.instance:
            exists = exists.exclude(pk=self.instance.pk)

        if exists.exists():
            raise serializers.ValidationError("You already have an identity with this name in this context.")

        return attrs

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
        
        if request and contexts: ## Validate that all contexts belong to the authenticated user
            for context in contexts:
                if context.owner != request.user:
                    raise serializers.ValidationError(f"You can only tag relationships with your own contexts.")

        if request and target_user == request.user: ## Prevent self-referential relationships
            raise serializers.ValidationError("You cannot create a relationship with yourself.")

        if not self.instance and request and target_user:  ## only gate NEW relationships 
            is_connected = ConnectionRequest.objects.filter(
                Q(sender=request.user, recipient=target_user) | Q(sender=target_user, recipient=request.user),
                status=ConnectionRequest.ACCEPTED,
            ).exists()
            if not is_connected:
                raise serializers.ValidationError("You can only create relationships with users you are connected to.")

        if not contexts: ## Relationship must have min 1 context
            raise serializers.ValidationError("Select at least one context.")

        exists = Relationship.objects.filter(owner=request.user, target_user=target_user) ## Duplicate relationship check

        if self.instance:
            exists = exists.exclude(pk=self.instance.pk)
        if exists.exists():
            raise serializers.ValidationError("Relationship already exists.")

        for context in contexts:
            if context.is_system: ## cannot use public context, meant for public visibility, not relationship tagging
                raise serializers.ValidationError("System context cannot be used as relationship tag.")
        
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
        field_name = attrs.get('field_name', getattr(self.instance, 'field_name', None))
        
        if request and identity.owner != request.user:
            raise serializers.ValidationError("You can only set disclosure rules for your own identities.")
        
        if request and context.owner != request.user:
            raise serializers.ValidationError("You can only use your own contexts for disclosure rules.")

        valid_field_names = {key for key, _ in DisclosureRule.FIELD_CHOICES}
        if identity:
            valid_field_names |= set(identity.attributes.values_list('key', flat=True))

        if field_name not in valid_field_names:
            raise serializers.ValidationError(f"'{field_name}' is not a valid field name for this identity.")
        
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


class DashboardSerializer(serializers.Serializer):
    me = serializers.DictField()
    identities = IdentityProfileSerializer(many=True)
    users = UserSearchSerializer(many=True)
    stats = serializers.DictField()
    

class LinkedAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedAccount
        fields = ['id', 'provider', 'provider_uid', 'raw_data', 'linked_at']
        read_only_fields = fields ## read only end to end, mutations handled by service layer, not serializer.

class ConnectionRequestSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = ConnectionRequest
        fields = ['id', 'sender_username', 'recipient_username', 'status', 'created_at', 'responded_at']
        read_only_fields = fields
        

## input serializer for sending a requet, same shape as LoginSerializer
# only parses/validates the presence of recipient_username bfore handing off to service.
class ConnectionRequestCreateSerializer(serializers.Serializer):
    recipient_username = serializers.CharField(required=True, trim_whitespace=True)

## dict-shaped output serializer for connection overview, each entry computed by RelationshipService.get_connection_overview.
class ConnectionOverviewSerializer(serializers.Serializer):
    username = serializers.CharField(source='other_user.username')
    state = serializers.CharField()
    request_id = serializers.IntegerField(required=False, allow_null=True)
    relationship_id = serializers.IntegerField(required=False, allow_null=True)