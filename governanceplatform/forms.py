from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import get_language_info
from django.utils.translation import gettext as _
from django_otp.forms import OTPAuthenticationForm
from parler.forms import TranslatableModelForm

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
    accept_terms = forms.BooleanField(
        label=_("I accept and agree to the"),
        error_messages={"required": _("You must accept the Terms of Use to register.")},
    )
    email = forms.TextInput()
    field_order = (
        "email",
        "last_name",
        "first_name",
        "password1",
        "password2",
        "accept_terms",
    )

    class Meta:
        model = User
        fields = (
            "email",
            "last_name",
            "first_name",
            "accept_terms",
        )


class CustomTranslatableAdminForm(TranslatableModelForm):
    FALLBACK_LANGUAGE = settings.PARLER_DEFAULT_LANGUAGE_CODE

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and self.FALLBACK_LANGUAGE not in self.data:
            if not self.instance.has_translation(self.FALLBACK_LANGUAGE):
                self.add_default_translation_error()
        elif self.FALLBACK_LANGUAGE not in self.data:
            self.add_default_translation_error()

        return cleaned_data

    def _post_clean(self):
        _post_clean = super()._post_clean()
        forms_to_check = ["QuestionCategoryForm"]
        if (
            self.instance.has_translation(self.instance.get_current_language())
            and self.__class__.__name__ in forms_to_check
        ):
            # get the model
            model = self._meta.model
            # get the language
            current_language = self.instance.get_current_language()
            # get the input value
            form_translation = self.cleaned_data.get('label')
            # check if this translations exists
            duplicate_translations = model.objects.translated(current_language).filter(
                translations__label=form_translation
            ).exclude(pk=self.instance.pk)  # Exclude the current instance

            if duplicate_translations.exists():
                error_message = _(
                    f"This {self.instance._meta.verbose_name.lower()} already exist."
                )
                self.add_error(
                    None,
                    ValidationError(error_message),
                )
        return _post_clean

    def add_default_translation_error(self):
        language_info = get_language_info(self.FALLBACK_LANGUAGE)
        fallback_language_name = language_info["name_translated"]
        error_message = _(
            "Default language translation (%(fallback_language_name)s) is missing. "
            "Please add it before saving."
        )
        self.add_error(
            None,
            ValidationError(
                error_message, params={"fallback_language_name": fallback_language_name}
            ),
        )


class TermsAcceptanceForm(forms.Form):
    accept = forms.BooleanField(label=_("I accept and agree to the"))
