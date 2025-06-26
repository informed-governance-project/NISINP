import httpx
from asgiref.sync import sync_to_async
from django.shortcuts import render
from django.http import HttpResponseServerError
from django.utils.translation import gettext_lazy as _

from governanceplatform.helpers import get_access_token_for_user


# generic synchron get
def generic_synchron_get(request, url, view):
    user = request.user
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


# generic asynchron get
async def generic_asynchron_get(request, url, view):
    render_async = sync_to_async(render, thread_sensitive=True)
    error_resp_async = sync_to_async(HttpResponseServerError, thread_sensitive=True)
    user = await sync_to_async(lambda: request.user)()
    token = await sync_to_async(get_access_token_for_user)(user)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return await error_resp_async(_("Error"))

    return await render_async(request, view, {"data": data})
