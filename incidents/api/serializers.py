from rest_framework import serializers

from incidents.models import User


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
