import functools
from django.shortcuts import redirect
from django.contrib import messages


def regulator_company_required(view_func, redirect_url="incidents"):
    """
        This decorator ensures that a user is linked to a company that is a regulator.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        for company in request.user.companies.all():
            if company.is_regulator:
                return view_func(request, *args, **kwargs)
        messages.info(
            request,
            "Only users that belong to a regulator's companies are allowed to access the page."
        )
        return redirect(redirect_url)
    return wrapper
