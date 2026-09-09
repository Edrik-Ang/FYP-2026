from django.contrib import admin
from .models import IdentityProfile, LinkedAccount, Relationship, DisclosureRule, Context, RelationshipContext

admin.site.register(IdentityProfile)
admin.site.register(Relationship)
admin.site.register(DisclosureRule)
admin.site.register(Context)
admin.site.register(RelationshipContext)
admin.site.register(LinkedAccount)

## Django admin creds for testing:
##username: admin
##password: password!1
## Test Users: John 
# password: testpass123


## postgresql: 
## login: postgres
## password: 1234