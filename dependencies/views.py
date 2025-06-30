from django.contrib.auth.decorators import login_required
from governanceplatform.api.v1.helpers import generic_asynchron_get, generic_synchron_get
from governanceplatform.settings import API_URL


@login_required
def full_sector_list_view(request):
    return generic_synchron_get(
        request,
        API_URL+"/api/v1/governanceplatform/sector/",
        "dependencies/dashboard.html",
    )


@login_required
async def full_sector_list_view_async(request):
    return await generic_asynchron_get(
        request,
        API_URL+"/api/v1/governanceplatform/sector/",
        "dependencies/dashboard.html",
    )
