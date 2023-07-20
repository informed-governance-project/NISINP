import secrets

from django.contrib.auth.models import Group


def generate_token():
    """Generates a random token-safe text string."""
    return secrets.token_urlsafe(32)[:32]


def user_in_group(user, group_name):
    """Check user group"""
    try:
        group = Group.objects.get(name=group_name)
        return user.groups.filter(id=group.id).exists()
    except Group.DoesNotExist:
        return False
