from django.utils.translation import gettext_lazy as _

# New flag used for logs
ADDITION = 1
CHANGE = 2
DELETION = 3
VIEW = 4
CONNECTION = 5
DECONNECTION = 6

ACTION_FLAG_CHOICES = {
    ADDITION: _("Addition"),
    CHANGE: _("Modification"),
    DELETION: _("Deletion"),
    # VIEW: _('View'),
    CONNECTION: _("Login"),
    DECONNECTION: _("Logout"),
}

# Functionalities list
FUNCTIONALITIES = {"securityobjectives": _("Security objective")}
