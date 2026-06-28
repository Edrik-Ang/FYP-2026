##main url.py file for the project. 
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include('identities.api_urls')),
    path('', include('identities.urls')),

]
