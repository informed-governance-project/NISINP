from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from governanceplatform.settings import TERMS_ACCEPTANCE_TIME_IN_DAYS

from governanceplatform.helpers import is_observer_user, is_user_operator, user_in_group


class RestrictViewsMiddleware:
    """
    Middleware that blocks URLs depending the user group.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            if user_in_group(user, "PlatformAdmin"):
                if request.path.startswith("/incidents/"):
                    return redirect(reverse("admin:index"))

            if is_observer_user(user):
                if (
                    request.path == reverse("declaration")
                    or request.path == reverse("regulator_incidents")
                    or request.path.startswith("/incidents/delete/")
                    or request.path.startswith("/incidents/incident/")
                    or request.path == reverse("create_workflow")
                    or request.path == reverse("edit_workflow")
                ):
                    return redirect(reverse("incidents"))

            if is_user_operator(user):
                if request.path.startswith(
                    "/incidents/incident/"
                ) or request.path == reverse("regulator_incidents"):
                    return redirect(reverse("incidents"))

        return self.get_response(request)


# check if the terms have been accepted
class TermsAcceptanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check for authenticated users
        if request.user.is_authenticated:
            # let the user logout
            if request.path == '/logout':
                return self.get_response(request)
            if not request.user.accepted_terms and request.path != '/accept_terms/':
                return redirect('accept_terms')
            # we want also to check the last checked
            if TERMS_ACCEPTANCE_TIME_IN_DAYS != 0:
                if request.user.accepted_terms_date is None and request.path != '/accept_terms/':
                    return redirect('accept_terms')
                if request.user.accepted_terms_date is not None and request.path != '/accept_terms/':
                    dt = now().date() - request.user.accepted_terms_date.date()
                    if dt.days > TERMS_ACCEPTANCE_TIME_IN_DAYS:
                        return redirect('accept_terms')
        return self.get_response(request)
