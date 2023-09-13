from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import UserApiElemView, UserApiView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="nisinp"),
    path(
        "swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="nisinp"),
        name="swagger-ui",
    ),
    path("redoc/", SpectacularRedocView.as_view(url_name="nisinp"), name="redoc"),
    path("user/", UserApiView.as_view()),
    path("user/<int:id>", UserApiElemView.as_view()),
]
