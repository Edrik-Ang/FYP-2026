# identities/views/search_views.py -- web-facing user search, filtered to discoverable
# users only. Replaces the old dashboard dropdown, which listed every registered user
# with no is_discoverable filter at all.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render

User = get_user_model()


@login_required
def user_search_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = User.objects.exclude(id=request.user.id).filter(
            profile__is_discoverable=True, username__icontains=query,
        ).order_by('username')
    return render(request, 'identities/user_search.html', {'query': query, 'results': results})