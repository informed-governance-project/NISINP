import httpx
from django.shortcuts import render
from django.http import HttpResponseServerError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required

from governanceplatform.helpers import get_access_token_for_user


def generic_synchron_get(request, user, url, view):
    token = get_access_token_for_user(user)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        print(f"Error when calling API: {e}")
        return HttpResponseServerError(_("Error"))

    return render(request, view, {"data": data})


@login_required
def full_sector_list_view(request):
    return generic_synchron_get(
        request,
        request.user,
        "http://127.0.0.1:8000/api/v1/governanceplatform/sector/",
        "dependencies/dashboard.html",
    )
