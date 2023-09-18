from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from governanceplatform.models import Company, User
from incidents.models import Incident

from .serializers import (
    CompanySerializer,
    IncidentSerializer,
    UserInputSerializer,
    UserSerializer,
)


#
# Model: User
#
class UserApiView(APIView):
    # add permission to check if user is authenticated
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(request=None, responses=UserSerializer)
    def get(self, request, *args, **kwargs):
        """
        List all the users.
        """
        objects = User.objects.all()
        serializer = UserSerializer(objects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Create a new object
    @extend_schema(request=UserInputSerializer, responses=UserSerializer)
    def post(self, request, *args, **kwargs):
        """
        Create a new user.
        """
        password = request.data.pop("password")
        new_user = User.objects.create(**request.data)
        new_user.set_password(password)
        new_user.save()
        serializer = UserSerializer(new_user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserApiElemView(GenericAPIView):
    # add permission to check if user is authenticated
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = UserSerializer

    @extend_schema(request=UserInputSerializer, responses=UserSerializer)
    def put(self, request, id=None):
        """
        Update an existing user.
        """
        user = User.objects.get(id=id)
        password = request.data.get("password", None)
        proxy_token = request.data.get("proxy_token", None)
        if password:
            user.set_password(password)
        if proxy_token:
            user.proxy_token = proxy_token
        user.save()
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


#
# Model: Company
#
class CompanyApiView(APIView):
    # add permission to check if user is authenticated
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(request=None, responses=CompanySerializer)
    def get(self, request, *args, **kwargs):
        """
        List all the companies.
        """
        objects = Company.objects.all()
        serializer = CompanySerializer(objects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


#
# Model: Incident
#
class IncidentApiView(APIView):
    # add permission to check if user is authenticated
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(request=None, responses=IncidentSerializer)
    def get(self, request, *args, **kwargs):
        """
        List all the companies.
        """
        objects = Incident.objects.all()
        serializer = IncidentSerializer(objects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
