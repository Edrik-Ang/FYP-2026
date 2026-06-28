## api.py file for API endpoints in the idnetities app.
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from .models import IdentityProfile, Relationship, DisclosureRule
from .serializers import (
    RegisterSerializer,
    IdentityProfileSerializer,
    RelationshipSerializer,
    DisclosureRuleSerializer
)

User = get_user_model()

### API response when user register, returns the token and username
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'token': token.key, 
                    'username': user.username,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
## API response when user log in, returns the token and username
class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'token': token.key,
                    'username': user.username,
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
## API resposne when user log out, deletes the token and returns 204 status code
class LogoutAPIView(APIView):
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
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
## Profile View (disclosure engine)
class ProfileAPIView(APIView):
    def get(self, request, username):
        owner = get_object_or_404(User, username=username)

        try:
            relationship = Relationship.objects.get(
                owner=owner,
                target_user=request.user
            )
            rel_type = relationship.relationship_type
        except Relationship.DoesNotExist:
            rel_type = None

        identities = IdentityProfile.objects.filter(owner=owner)
        visible_data = []
        for identity in identities:
            disclosed_fields = DisclosureRule.objects.filter(
                identity=identity,
                relationship_type=rel_type,
                is_visible=True
            ).values_list('field_name', flat=True)

            filtered_identity = {}
            for field in disclosed_fields:
                filtered_identity[field] = getattr(identity, field)
            
            if filtered_identity:
                visible_data.append(filtered_identity)
        
        return Response({
            'owner': owner.username,
            'relationship_type': rel_type,
            'visible_identities': visible_data
        })
