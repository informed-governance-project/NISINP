from django.conf import settings
from django_otp.decorators import otp_required as _otp_required


def optional_otp_required(view):
    """
    Enforce OTP verification in production only.
    When DEBUG=True the decorator is a no-op so developers can work without 2FA.
    """
    if settings.DEBUG:
        return view
    return _otp_required(view)
