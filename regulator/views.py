from django.shortcuts import render

from governanceplatform.decorators import company_permission_required


@company_permission_required(is_regulator=True)
def index(request):
    return render(request, "regulator/index.html")
