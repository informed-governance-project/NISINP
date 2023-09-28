import secrets

from .models import User


def generate_token():
    """Generates a random token-safe text string."""
    return secrets.token_urlsafe(32)[:32]


def user_in_group(user, group_name) -> bool:
    """Check user group"""
    return any(user_group.name == group_name for user_group in user.groups.all())


def is_user_regulator(user: User) -> bool:
    return user_in_group(user, "RegulatorAdmin") or user_in_group(
        user, "RegulatorStaff"
    )


def get_company_session(request):
    company_in_use = request.session.get(
        "company_in_use", request.user.companies.first().id
    )
    if company_in_use:
        return request.user.companies.get(id=company_in_use)
    return False
