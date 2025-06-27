from rest_framework import viewsets
from governanceplatform.models import Sector
from .serializers import SectorSerializer
from .permissions import CreatorAndActionGroupPermission


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [CreatorAndActionGroupPermission]

    write_groups = ["RegulatorAdmin"]
    read_groups = ["RegulatorAdmin", "RegulatorUser"]

    allowed_groups = {
        "list": [
            "RegulatorAdmin", "RegulatorUser", "is_creator",
        ],
        "retrieve": [
            "RegulatorAdmin", "RegulatorUser", "is_creator",
        ],
        "create": ["RegulatorAdmin"],
        "update": ["RegulatorAdmin"],
        "partial_update": ["RegulatorAdmin"],
        "destroy": ["RegulatorAdmin"],
    }
