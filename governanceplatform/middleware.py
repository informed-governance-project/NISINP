from django.shortcuts import redirect
from django.urls import reverse

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
