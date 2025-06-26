from django.contrib.auth.decorators import login_required
from governanceplatform.api.v1.helpers import generic_asynchron_get, generic_synchron_get


@login_required
def full_sector_list_view(request):
    return generic_synchron_get(
        request,
        "http://127.0.0.1:8000/api/v1/governanceplatform/sector/",
        "dependencies/dashboard.html",
    )


@login_required
async def full_sector_list_view_async(request):
    return await generic_asynchron_get(
        request,
        "http://127.0.0.1:8000/api/v1/governanceplatform/sector/",
        "dependencies/dashboard.html",
    )
