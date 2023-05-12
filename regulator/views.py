from django.shortcuts import render
from governanceplatform.decorators import regulator_required

@regulator_required
def index(request):
    return render(request, "regulator/index.html")
