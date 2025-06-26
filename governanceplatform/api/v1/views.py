from rest_framework import viewsets
from governanceplatform.models import Sector
from .serializers import SectorSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
