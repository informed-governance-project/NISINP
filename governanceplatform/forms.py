from django import forms
from django.contrib.auth.forms import UserCreationForm
from django_otp.forms import OTPAuthenticationForm

# from governanceplatform.models import User
from django.contrib.auth import get_user_model


User = get_user_model()


class AuthenticationForm(OTPAuthenticationForm):
    otp_device = forms.CharField(required=False, widget=forms.HiddenInput)
    otp_challenge = forms.CharField(required=False, widget=forms.HiddenInput)


class SelectCompany(forms.Form):
    select_company = forms.ModelChoiceField(
        queryset=None, required=False, label="Company"
    )

    def __init__(self, *args, **kwargs):
        companies = kwargs.pop("companies")
        super().__init__(*args, **kwargs)

        self.fields["select_company"].queryset = companies.order_by("name")


class RegistrationForm(UserCreationForm):
    email = forms.TextInput()
    field_order = ('email', "last_name", "first_name", 'password1', 'password2',)

    class meta:
        model = User
        fields = ("email", "last_name", "first_name",)
