import secrets


def generate_token():
    """Generates a random token-safe text string."""
    return secrets.token_urlsafe(32)[:32]
