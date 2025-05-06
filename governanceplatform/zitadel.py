import requests
import time
import jwt
import json
import uuid
import base64

from . import settings
# from .validators import ZitadelIntrospectTokenValidator

USER_SERVICE_PRIVATE_KEY_FILE = {}


def create_zitadel_user(user, request):
    token = get_zitadel_token()

    # check if the token is valid
    # ins = ZitadelIntrospectTokenValidator()
    # ins(token_string=token, scopes=None, request=request)

    # re-encode the salt in base64 to have the same like the zitadel one
    algo, iterations, salt, digest = user.password.split('$')
    salt_byte = salt.encode("ascii")
    b64_byte_salt = base64.b64encode(salt_byte)
    b64_salt = b64_byte_salt.decode("ascii")

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "userId": str(uuid.uuid4()),
        "username": user.email,
        "profile": {
            "givenName": user.first_name,
            "familyName": user.last_name,
            "displayName": f"{user.first_name} {user.last_name}".strip() or "N/A",
            "preferredLanguage": "en",
        },
        "email": {
            "email": user.email,
            "isVerified": True,
        },
        # "password": {"password": password, "changeRequired": True},
        # correct format for hash password in zitadel
        "hashedPassword": {
            "hash": '$pbkdf2-sha256$27500$'+b64_salt+'$'+digest,
            "changeRequired": False
        },
    }

    response = requests.post(settings.JWT_DOMAIN+"/v2/users/human", headers=headers, json=payload)
    print("Response create zitadel user:", response.text)
    response.raise_for_status()
    return response.json()


def get_zitadel_token():
    client_assertion = generate_client_assertion()
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "scope": f"""openid profile email urn:zitadel:iam:org:project:id:zitadel:aud urn:zitadel:iam:org:project:id:{settings.ZITADEL_PROJECT_ID}:aud""",
        "assertion": client_assertion,
    }
    response = requests.post(settings.JWT_OAUTH_URL, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def generate_client_assertion():
    with open(settings.USER_SERVICE_PRIVATE_KEY_FILE_PATH, "r") as f:
        data = json.load(f)
        USER_SERVICE_PRIVATE_KEY_FILE["user_id"] = data["userId"]
        USER_SERVICE_PRIVATE_KEY_FILE["key_id"] = data["keyId"]
        USER_SERVICE_PRIVATE_KEY_FILE["private_key"] = data["key"]
    payload = {
        "iss": USER_SERVICE_PRIVATE_KEY_FILE["user_id"],
        "sub": USER_SERVICE_PRIVATE_KEY_FILE["user_id"],
        "aud": settings.JWT_DOMAIN,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 24,
    }
    headers = {
        "alg": "RS256",
        "kid": USER_SERVICE_PRIVATE_KEY_FILE["key_id"]
    }

    client_assertion = jwt.encode(
        headers=headers,
        payload=payload,
        key=USER_SERVICE_PRIVATE_KEY_FILE["private_key"],
        algorithm="RS256",
    )
    return client_assertion
