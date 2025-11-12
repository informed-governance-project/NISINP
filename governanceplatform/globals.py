from django.utils.translation import gettext_lazy as _


def get_functionality_choices():
    return FUNCTIONALITIES


# New flag used for logs
ADDITION = 1
CHANGE = 2
DELETION = 3
VIEW = 4
CONNECTION = 5
DECONNECTION = 6
EXPORT = 7

ACTION_FLAG_CHOICES = {
    ADDITION: _("Addition"),
    CHANGE: _("Modification"),
    DELETION: _("Deletion"),
    # VIEW: _('View'),
    CONNECTION: _("Login"),
    DECONNECTION: _("Logout"),
    EXPORT: _("Export"),
}

# Functionalities list
FUNCTIONALITIES = {"securityobjectives": _("Security objective")}
