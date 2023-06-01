from django.urls import re_path
from revproxy.views import ProxyView

urlpatterns = [
    re_path(r"(?P<path>.*)", ProxyView.as_view(upstream="http://example.com/")),
    re_path(
        r"^notifications/(?P<path>.*)$",
        ProxyView.as_view(upstream="http://127.0.0.1:5002/"),
    ),
]
