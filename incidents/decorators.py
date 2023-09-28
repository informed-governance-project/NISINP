import functools

from django.contrib import messages
from django.shortcuts import redirect

from governanceplatform.helpers import is_user_regulator


def regulator_company_required(view_func, redirect_url="/"):
    """
    This decorator ensures that a user is linked to a company that is a regulator.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        company_id = request.session.get("company_in_use")
        if company_id and is_user_regulator(request.user):
            # Iterate through users' companies to make sure the access is not withdrawn.
            for user_company in request.user.companies:
                if user_company.id == company_id and user_company.is_regulator:
                    return view_func(request, *args, **kwargs)

        messages.info(
            request,
            "Only users that belong to a regulator's companies are allowed to access the page.",
        )

        return redirect(redirect_url)

    return wrapper
