import functools

from django.contrib import messages
from django.shortcuts import redirect

from governanceplatform.helpers import is_user_regulator


def regulator_role_required(view_func, redirect_url="/"):
    """
    This decorator ensures that a logged in user has a regulator role.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if is_user_regulator(request.user):
            return view_func(request, *args, **kwargs)

        messages.info(request, "User must be have a regulator role to access the page.")
        return redirect(redirect_url)

    return wrapper
