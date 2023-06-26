from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect


def company_permission_required(
    is_regulator=False, redirect_field_name=REDIRECT_FIELD_NAME, login_url="login"
):
    def decorator(view_func):
        @wraps(view_func)
        @user_passes_test(
            lambda u: u.is_active,
            login_url=login_url,
            redirect_field_name=redirect_field_name,
        )
        def wrapped_view(request, *args, **kwargs):
            company_in_use = request.session.get(
                "company_in_use", request.user.companies.first().id
            )
            if company_in_use:
                company_selected = request.user.companies.get(id=company_in_use)
                if company_selected:
                    if is_regulator and company_selected.is_regulator:
                        return view_func(request, *args, **kwargs)
                    elif not is_regulator and not company_selected.is_regulator:
                        return view_func(request, *args, **kwargs)
            return redirect(login_url)

        return wrapped_view

    return decorator


def administrator_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url="login"
):
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_administrator,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
