## api.py file for API endpoints in the identities app.
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from .models import IdentityProfile, Relationship, DisclosureRule, Context
from .serializers import (
    RegisterSerializer,
    IdentityProfileSerializer,
    RelationshipSerializer,
    DisclosureRuleSerializer, 
    ContextSerializer,
    UserSearchSerializer,
    VisibleIdentitySerializer
)
from .disclosure import get_effective_contexts, get_visible_fields

User = get_user_model()

## RegisterAPIView handles user registration, returns auth token and username on successful registration.
## uses RegisterSerializer to validate and create new users, and generates an auth token for the newly created user.
class RegisterAPIView(generics.CreateAPIView):
    """POST /api/register/ - create a new user (+ default public context), returns an auth token.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    ## custom create method to handle user registration and token creation
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) 
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'username': user.username, 'token': token.key}, status=status.HTTP_201_CREATED)     

    # def post(self, request):
    #     serializer = RegisterSerializer(data=request.data)
    #     if serializer.is_valid():
    #         user = serializer.save()
    #         token, _ = Token.objects.get_or_create(user=user)
    #         return Response(
    #             {
    #                 'token': token.key, 
    #                 'username': user.username,
    #             },
    #             status=status.HTTP_201_CREATED
    #         )
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    ##Include OIDC login and registration endpoints for third-party authentication providers. 
    # This will allow users to log in or register using their existing accounts from providers like Google, Facebook, or GitHub.

    
## LoginAPIView class handles user login, returns auth token and username on successful authentication.
# Uses the authenticate method to verify user credentials and generates an auth token for the authenticated user. 
class LoginAPIView(APIView):
    """POST /api/login/ - exchanges username-password for an auth token."""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'username':user.username,'token': token.key})


## LogoutAPIView class handles user logouts, delete the auth token for authenticated users.
# This ensures that the user is logged out and cannot use the token for further authentication.        
class LogoutAPIView(APIView):
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

## ContextListCreateView class allows users to list and create contexts
# Uses context serializer to serialize the data and requires the user to be authenticated.
class ContextListCreateView(generics.ListCreateAPIView):
    serializer_class = ContextSerializer
    def get_queryset(self):
        return Context.objects.filter(owner=self.request.user)
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

## ContextDetailView class allows users to retrieve, update, and delete a specific context.
# Uses context serializer to serialize the data and requires the user to be authenticated.
class ContextDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContextSerializer
    def get_queryset(self):
        return Context.objects.filter(owner=self.request.user)
    def perform_destroy(self, instance):
        if instance.is_public_default:
            raise ValidationError("Cannot delete the default public context.")
        instance.delete()
    
### APIs for the identities
##This API view allows users to list and create identity profiles. It uses the IdentityProfileSerializer to serialize the data and requires the user to be authenticated.
class IdentityListCreateView(generics.ListCreateAPIView):
    serializer_class = IdentityProfileSerializer
    def get_queryset(self):
        return IdentityProfile.objects.filter(owner=self.request.user)
    def perform_create(self,serializer):
        serializer.save(owner=self.request.user) ####When creating a new identity, the owner is set to the currently authenticated user.
    
class IdentityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IdentityProfileSerializer
    def get_queryset(self):
        return IdentityProfile.objects.filter(owner=self.request.user)
    
### APIs for the relationships
##This api view allows users to list and create relationships. Uses relationship serializer and requires user to be authenticated.
class RelationshipListCreateView(generics.ListCreateAPIView):
    serializer_class = RelationshipSerializer
    def get_queryset(self):
        return Relationship.objects.filter(owner=self.request.user)
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class RelationshipDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = RelationshipSerializer
    def get_queryset(self):
        return Relationship.objects.filter(owner=self.request.user)

## Disclosure rules API

##this api will create and list disclosure rules for a specific identity. It uses the DisclosureRuleSerializer to serialize the data and requires the user to be authenticated.
class DisclosureRuleListCreateView(generics.ListCreateAPIView):
    serializer_class = DisclosureRuleSerializer
    def get_queryset(self):
        return DisclosureRule.objects.filter(
            identity__owner=self.request.user
        )

## this api will retrieve, update, and delete a specific disclosure rule. It uses the DisclosureRuleSerializer to serialize the data and requires the user to be authenticated.
class DisclosureRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DisclosureRuleSerializer
    def get_queryset(self):
        return DisclosureRule.objects.filter(
            identity__owner=self.request.user
        )
## ProfileAPIView class retrieves profile information for a specific user based on username. 
# Uses VisibleIdentitySerialzier to serialize the data and requires the user to be authenticated.
class ProfileAPIView(APIView):
    def get(self, request, username):
        owner = get_object_or_404(User, username=username)
        identities = IdentityProfile.objects.filter(owner=owner)
        
        if owner == request.user:
            visible_data = [
                {
                    'identity_id': i.id, 'context_name': i.context.name,
                    'visible_fields':{
                        f:getattr(i,f) for f, _ in DisclosureRule.FIELD_CHOICES},
                } for i in identities
            ]
        else:
            viewer_contexts = get_effective_contexts(owner, request.user)
            visible_data = []
            for identity in identities:
                fields = get_visible_fields(identity, viewer_contexts)
                if fields:
                    visible_data.append({
                        'identity_id': identity.id, 'context_name': identity.context.name,
                        'visible_fields': {f: getattr(identity, f) for f in fields},
                    })

        serializer = VisibleIdentitySerializer(visible_data, many=True)
        return Response({'owner': owner.username, 'visible_identities':serializer.data})


class UserSearchAPIView(generics.ListAPIView):
    """
    GET /api/users/?search=<query> -- lists other users by username.
    No search param returns everyone (mirror the dashboard's show all user MVP behavior)."""
    serializer_class = UserSearchSerializer
    def get_queryset(self):
        queryset = User.objects.exclude(id=self.request.user.id)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(username__icontains=search)
        return queryset.order_by('username')
