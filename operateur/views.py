from django.shortcuts import render
from governanceplatform.decorators import operateur_required


@operateur_required
def index(request):
    return render(request, "operateur/index.html")
