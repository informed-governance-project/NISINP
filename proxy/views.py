from django.core.exceptions import MultipleObjectsReturned
from revproxy.views import ProxyView

from .models import ExternalToken


class DefaultProxyView(ProxyView):
    # upstream = "http://127.0.0.1:5000/"

    def get_proxy_request_headers(self, request):
        # print(self.upstream)
        # print(request.user)
        headers = super().get_proxy_request_headers(request)

        module_path = request.path.strip("/").split("/")[0]
        try:
            external_token = ExternalToken.objects.get(
                user=request.user, module__path=module_path
            )
            print(external_token.token)
        except ExternalToken.DoesNotExist:
            # return the headers without the authentication token
            # users should be blocked by the proxified module
            return headers
        except MultipleObjectsReturned:
            return headers

        headers["Proxy-Token"] = external_token.token
        headers["X-Forwarded-Prefix"] = module_path
        headers["X-Script-Name"] = module_path
        print(headers)
        return headers
