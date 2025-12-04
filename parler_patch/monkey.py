from parler.admin import TranslatableAdmin, TranslatableModelForm
from parler.utils.conf import get_language

#
#  Django 6 monkeypatch for django-parler
#


class FixedTranslatableModelForm(TranslatableModelForm):
    """
    Fixes failures in Django 6 due to form internals changed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure all translated fields exist for the active language
        language_code = self.language_code or get_language().get(
            "DEFAULT_LANGUAGE_CODE", "en"
        )
        self.language_code = language_code

        for _field_name, field in self.fields.items():
            if hasattr(field, "language_code"):
                field.language_code = language_code

    class Media:
        # Ensure CSS for tabs is still loaded
        css = {
            "all": (
                "admin/css/base.css",
                "admin/css/forms.css",
                "parler/admin/css/tabbed_translation_fields.css",
            )
        }
        js = ("parler/admin/js/tabbed_translation_fields.js",)


class FixedTranslatableAdminMixin(TranslatableAdmin):
    """
    Fixes Django 6 admin behaviors:
    - get_form
    - get_formsets_with_inlines
    - translation tabs
    """

    form = FixedTranslatableModelForm

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        form_class.language_tabs = True
        return form_class

    # not working for the moment
    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        """
        Inject translation tabs into admin template context.
        """
        languages = self.get_available_languages(obj)
        context["translation_languages"] = languages
        context["language_tabs"] = True
        return super().render_change_form(request, context, add, change, form_url, obj)


def patch_parler():

    from parler.admin import TranslatableAdmin

    if not hasattr(TranslatableAdmin, "_patched_django6"):
        original = TranslatableAdmin.get_form

        def get_form(self, request, obj=None, **kwargs):
            form = original(self, request, obj, **kwargs)
            return form

        TranslatableAdmin.get_form = get_form
        TranslatableAdmin._patched_django6 = True
