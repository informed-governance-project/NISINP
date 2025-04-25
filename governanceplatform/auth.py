from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from .models import User


class CustomOIDCBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        email = claims.get("email")
        claims.pop("email", None)  # avoid error
        # claims.pop("sub", None)  # avoid error
        claims.pop("email_verified", None)  # avoid error
        first_name = claims.get("given_name", "")
        last_name = claims.get("family_name", "")

        user = User.objects.create_user(
            email=email,
            password="AbstractBaseUser().make_random_password()",
            first_name=first_name,
            last_name=last_name,
        )
        return user
