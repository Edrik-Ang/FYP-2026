from django.contrib import admin
from .models import IdentityProfile, Relationship, DisclosureRule, Context, RelationshipContext

admin.site.register(IdentityProfile)
admin.site.register(Relationship)
admin.site.register(DisclosureRule)
admin.site.register(Context)
admin.site.register(RelationshipContext)

## Django admin creds for testing:
##username: admin
##password: password!1
## Test Users: John 
# password: testpass123


## postgresql: 
## login: postgres
## password: password