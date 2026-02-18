from django.conf import settings
from django.db import models
from django.utils.translation import get_language


class TranslatableModel(models.Model):
    class Meta:
        abstract = True

    def get_translation(self, language_code):
        return self.translations.filter(language_code=language_code).first()

    def safe_translation_getter(
        self,
        field,
        language_code=None,
        any_language=False,
    ):
        language_code = language_code or get_language()

        # asked language
        translation = self.get_translation(language_code)
        if translation:
            value = getattr(translation, field, None)
            if value:
                return value

        # fallback
        if any_language:
            for lang, _ in settings.LANGUAGES:
                translation = self.get_translation(lang)
                if translation:
                    value = getattr(translation, field, None)
                    if value:
                        return value

        return None


class BaseTranslation(models.Model):
    language_code = models.CharField(max_length=15)

    class Meta:
        abstract = True
