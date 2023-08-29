from django.contrib.auth import login
from django.http import HttpResponseForbidden, HttpResponseRedirect

from .models import User


class proxyPortalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the value of the Authorization header
        print("Hit")
        # request.path = request.path
        # request.path_info = "/governance1" + request.path_info
        if not request.user.is_authenticated:
            token = request.headers.get("Proxy-Token", None)

            # When proxy is not used
            if token is None:
                print("Token is None")
                return self.get_response(request)

            user = User.objects.filter(proxy_token=token)
            if not user.exists():
                return HttpResponseForbidden("Invalid token")

            user = user.first()
            if user is not None:
                print("Loging in...")
                login(request, user)

            # Set the user for the request
            request.user = user
        else:
            print("Already authenticated")
            print(request.user)
        return self.get_response(request)
