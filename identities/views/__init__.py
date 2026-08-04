from .views import home_view, dashboard_view, profile_redirect_view, profile_view
from .auth_views import WebLoginView, WebLogoutView, register_view
from .context_views import (
    context_list_view, context_create_view, context_delete_view, context_edit_view)
from .identity_views import (identity_list_view, identity_create_view, identity_edit_view, identity_delete_view)
from .relationship_views import ( relationship_list_view, relationship_create_view, relationship_edit_view, relationship_delete_view)
from .disclosure_views import (disclosure_rule_list_view, disclosure_rule_create_view, disclosure_rule_edit_view, disclosure_rule_delete_view)
# from .integration_views import ...