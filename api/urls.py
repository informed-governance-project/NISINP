from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import CompanyApiView, IncidentApiView, UserApiView, UserElementApiView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="api"),
    path(
        "swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="api"),
        name="swagger-ui",
    ),
    path("redoc/", SpectacularRedocView.as_view(url_name="api"), name="redoc"),
    path("user/", UserApiView.as_view()),
    path("user/<int:id>", UserElementApiView.as_view()),
    path("company/", CompanyApiView.as_view()),
    path("incident/", IncidentApiView.as_view()),
]
