from rest_framework import serializers

from governanceplatform.models import Company, Service, User
from incidents.models import Incident, RegulationType


#
# Model: User
#
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_staff",
        ]


class UserInputSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True, help_text="Email of the user.", label="Email"
    )
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(max_length=200, required=True)
    phone_number = serializers.CharField(max_length=30)
    proxy_token = serializers.CharField(max_length=255)
    is_staff = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "password",
            "phone_number",
            "proxy_token",
            "is_staff",
        ]


#
# Model: Company
#
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "country",
            "email",
            "is_regulator",
            "sectors",
        ]


#
# Model: Service
#
class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "name",
        ]


#
# Model: RegulationType
#
class RegulationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationType
        fields = [
            "label",
        ]


#
# Model: Incident
#
class IncidentSerializer(serializers.ModelSerializer):
    affected_services = ServiceSerializer(read_only=True, many=True)
    regulations = RegulationTypeSerializer(read_only=True, many=True)

    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "preliminary_notification_date",
            "final_notification_date",
            "company_name",
            "affected_services",
            "regulations",
            "is_significative_impact",
        ]
