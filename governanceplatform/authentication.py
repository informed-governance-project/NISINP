from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
 
class CustomAuth(BaseBackend):
    def authenticate(self, request, **kvargs):
        try:
            user = User.objects.get(email=kvargs['username'])
            if user.check_password(kvargs['password']):
                return user
        except:
            pass


    def get_user(self, user_id):
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return None