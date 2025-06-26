from rest_framework import serializers
from governanceplatform.models import Sector


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = '__all__'
        ordering = ['-id']
