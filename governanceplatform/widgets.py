from import_export import widgets
from parler.models import TranslationDoesNotExist

from .settings import LANGUAGES


# Custom widget to handle translated M2M relationships
class TranslatedNameM2MWidget(widgets.ManyToManyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return self.model.objects.none()

        names = value.split(self.separator)
        languages = [lang[0] for lang in LANGUAGES]

        instances = []
        for name in names:
            for lang_code in languages:
                try:
                    instance = self.model._parler_meta.root_model.objects.get(
                        **{self.field: name.strip()},
                        language_code=lang_code,
                    )
                    instances.append(instance.master_id)
                    break
                except (self.model.DoesNotExist, TranslationDoesNotExist):
                    pass

        return instances


# Custom widget to handle translated ForeignKey relationships
class TranslatedNameWidget(widgets.ForeignKeyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return self.model.objects.none()

        languages = [lang[0] for lang in LANGUAGES]

        for lang_code in languages:
            try:
                instance = self.model._parler_meta.root_model.objects.get(
                    **{self.field: value.strip()},
                    language_code=lang_code,
                )
                return instance.master
            except (self.model.DoesNotExist, TranslationDoesNotExist):
                pass

        return


# Custom widget to get the translation of an unrelated object in a model
class TranslatedObjectNotInTheModelWidget(widgets.ForeignKeyWidget):

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return self.model.objects.none()

        languages = [lang[0] for lang in LANGUAGES]

        for lang_code in languages:
            try:
                if isinstance(value, int):
                    value = self.model.objects.get(pk=value)
                instance = self.model._parler_meta.root_model.objects.get(
                    **{self.field: value},
                    language_code=lang_code,
                )

                return instance.master
            except (self.model.DoesNotExist, TranslationDoesNotExist):
                pass

        return
