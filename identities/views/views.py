## views.py file contains the view functions for the identities app, including home, dashboard, and profile views.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from identities.services.dashboard_service import DashboardService
from ..disclosure import get_visible_identities, get_effective_contexts

User = get_user_model()


def home_view(request):
    return render(request, 'identities/home.html')


@login_required
def dashboard_view(request):
    dashboard = DashboardService.get_dashboard(request.user)
    return render(request, "identities/dashboard.html", dashboard)



@login_required
def profile_redirect_view(request):
    username = request.GET.get('username')
    if not username:
        return redirect("dashboard")
    return redirect('profile', username=username)


@login_required
def profile_view(request, username):
    owner = get_object_or_404(User, username=username)
    visible_data = get_visible_identities(owner, request.user)

    viewer_contexts = None
    if owner != request.user:
        viewer_contexts = get_effective_contexts(owner, request.user)

    return render(request, 'identities/profile.html', {'owner': owner, 'visible_data': visible_data, 'viewer_contexts': viewer_contexts})


