from django.shortcuts import render

def index(request):
    return render(request, "html/operateur/index.html")