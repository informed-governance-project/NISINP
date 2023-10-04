from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext as _
from django_otp.forms import OTPAuthenticationForm

User = get_user_model()


class AuthenticationForm(OTPAuthenticationForm):
    otp_device = forms.CharField(required=False, widget=forms.HiddenInput)
    otp_challenge = forms.CharField(required=False, widget=forms.HiddenInput)


class CustomUserChangeForm(UserChangeForm):
    password = None

    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.CharField(
        disabled=True,
        required=True,
        widget=forms.EmailInput(attrs={"readonly": "readonly"}),
    )

    role = forms.CharField(
        label=_("Role"),
        disabled=True,
        required=False,
        widget=forms.TextInput(attrs={"readonly": "readonly"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone_number", "role")
        widgets = {
            "email": forms.TextInput(attrs={"readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        group_names = [group.name for group in self.instance.groups.all()]

        if not group_names:
            del self.fields["role"]
        else:
            role = ", ".join(group_names)
            self.fields["role"].initial = role

    def clean(self):
        cleaned_data = super().clean()

        # Validate readonly fields
        self.validate_readonly_fields(cleaned_data)

        # Validate groups
        self.validate_groups(cleaned_data)

        return cleaned_data

    def validate_readonly_fields(self, cleaned_data):
        readonly_fields = ["email"]
        for field_name in readonly_fields:
            old_value = getattr(self.instance, field_name)
            new_value = cleaned_data.get(field_name)

            if new_value and new_value != old_value:
                raise forms.ValidationError(
                    f"{field_name.capitalize()} cannot be modified."
                )

    def validate_groups(self, cleaned_data):
        actual_group_names = {group.name for group in self.instance.groups.all()}
        form_group_names = set(cleaned_data.get("role", "").split(", "))
        if form_group_names != actual_group_names:
            raise forms.ValidationError("Groups cannot be modified.")


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
    field_order = (
        "email",
        "last_name",
        "first_name",
        "password1",
        "password2",
    )

    class meta:
        model = User
        fields = (
            "email",
            "last_name",
            "first_name",
        )
