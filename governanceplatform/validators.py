from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

import time
import json
import jwt
from typing import Dict

from authlib.oauth2.rfc7662 import IntrospectTokenValidator
import requests
from . import settings

API_PRIVATE_KEY_FILE = {}


class ValidatorError(Exception):
    def __init__(self, error: Dict[str, str], status_code: int):
        super().__init__()
        self.error = error
        self.status_code = status_code


class ZitadelIntrospectTokenValidator(IntrospectTokenValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_api_private_key(settings.API_PRIVATE_KEY_FILE_PATH)

    @staticmethod
    def load_api_private_key(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            API_PRIVATE_KEY_FILE["client_id"] = data["clientId"]
            API_PRIVATE_KEY_FILE["key_id"] = data["keyId"]
            API_PRIVATE_KEY_FILE["private_key"] = data["key"]

    def introspect_token(self, token_string):
        # Create JWT for client assertion
        payload = {
            "iss": API_PRIVATE_KEY_FILE["client_id"],
            "sub": API_PRIVATE_KEY_FILE["client_id"],
            "aud": settings.JWT_DOMAIN,
            "exp": int(time.time()) + 60 * 60,  # Expires in 1 hour
            "iat": int(time.time()),
        }
        headers = {"alg": settings.JWT_SIGN_ALGORITHM, "kid": API_PRIVATE_KEY_FILE["key_id"]}
        jwt_token = jwt.encode(
            payload=payload,
            key=API_PRIVATE_KEY_FILE["private_key"],
            algorithm="RS256",
            headers=headers,

        )

        # Send introspection request
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": jwt_token,
            "token": token_string,
        }
        response = requests.post(
            settings.JWT_INTROSPECTION_URL, headers=headers, data=data
        )

        response.raise_for_status()
        token_data = response.json()
        return token_data

    def match_token_scopes(self, token, or_scopes):
        if or_scopes is None:
            return True
        scopes = token.get("scope", "").split()
        for and_scopes in or_scopes:
            if all(key in scopes for key in and_scopes.split()):
                return True
        return False

    def validate_token(self, token, scopes, request):
        now = int(time.time())
        if not token:
            raise ValidatorError(
                {"code": "invalid_token_revoked", "description": "Token was revoked."},
                401,
            )
        if not token.get("active"):
            raise ValidatorError(
                {"code": "invalid_token_inactive", "description": "Token is inactive."},
                401,
            )
        if token["exp"] < now:
            raise ValidatorError(
                {"code": "invalid_token_expired", "description": "Token has expired."},
                401,
            )
        if not self.match_token_scopes(token, scopes):
            raise ValidatorError(
                {
                    "code": "insufficient_scope",
                    "description": f"Token has insufficient scope. Route requires: {scopes}",
                },
                401,
            )

    def __call__(self, token_string, scopes, request):
        token = self.introspect_token(token_string)
        self.validate_token(token, scopes, request)
        return token


class NoReusePasswordValidator:
    """
    Validator to ensure users don't reuse previously used passwords.
    """

    def validate(self, password, user=None):
        if user or user.pk is None:
            return

        if user.check_password(password):
            raise ValidationError(
                _("Your new password must differ from your current password."),
                code="password_same_as_current",
            )

        old_passwords = user.passworduserhistory_set.all().values_list(
            "hashed_password", flat=True
        )

        for old_password in old_passwords:
            # Temporarily set the old hashed password
            user.password = old_password
            if user.check_password(password):
                raise ValidationError(
                    _("Reusing a previously used password is not permitted."),
                    code="password_reuse",
                )

    def get_help_text(self):
        return _("Your password must not match any previously used passwords.")
