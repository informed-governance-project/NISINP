from rest_framework import viewsets
from governanceplatform.models import Sector
from .serializers import SectorSerializer
from .permissions import GroupBasedPermission


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [GroupBasedPermission]

    write_groups = ["regulatorAdmin"]
    read_groups = ["regulatorAdmin", "regulatorUser"]
