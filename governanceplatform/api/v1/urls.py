from rest_framework.routers import DefaultRouter
from .views import SectorViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'sector', SectorViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
