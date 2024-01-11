from parler_rest.fields import TranslatedFieldsField
from parler_rest.serializers import TranslatableModelSerializer
from rest_framework import serializers

from governanceplatform.models import Company, Regulation, Service, User
from incidents.models import Incident


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
    email = serializers.CharField(max_length=200, required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(max_length=200, required=True)
    phone_number = serializers.CharField(max_length=30)
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
            "sectors",
        ]


#
# Model: Service
#
class ServiceSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=Service)

    class Meta:
        model = Service
        fields = [
            "translations",
        ]


#
# Model: Regulation
#
class RegulationSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=Service)

    class Meta:
        model = Regulation
        fields = [
            "translations",
        ]


#
# Model: Incident
#
class IncidentSerializer(serializers.ModelSerializer):
    affected_services = ServiceSerializer(read_only=True, many=True)
    regulations = RegulationSerializer(read_only=True, many=True)

    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "company_name",
            "affected_services",
            "regulations",
            "is_significative_impact",
        ]
