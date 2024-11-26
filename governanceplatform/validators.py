from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NoReusePasswordValidator:
    """
    Validator to ensure users don't reuse previously used passwords.
    """

    def validate(self, password, user=None):
        if user is None:
            return

        if user.check_password(password):
            raise ValidationError(
                _("Your new password cannot be the same as your current password."),
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
                    _("You cannot reuse a previously used password."),
                    code="password_reuse",
                )

    def get_help_text(self):
        return _("Your password must not match any previously used passwords.")
