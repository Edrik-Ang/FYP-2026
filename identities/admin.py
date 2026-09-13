from django.contrib import admin
from .models import IdentityProfile, LinkedAccount, Relationship, DisclosureRule, Context, RelationshipContext, ConnectionRequest

admin.site.register(IdentityProfile)
admin.site.register(Relationship)
admin.site.register(DisclosureRule)
admin.site.register(Context)
admin.site.register(RelationshipContext)
admin.site.register(ConnectionRequest)

@admin.register(LinkedAccount)
class LinkedAccountAdmin(admin.ModelAdmin):
    exclude = ('access_token', 'refresh_token')
## Django admin creds for testing:
##username: admin
##password: password!1
## Test Users: 'John' or 'Alice' or 'Bob' or 'Charlie' 
# password: testpass123