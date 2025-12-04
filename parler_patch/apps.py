from django.apps import AppConfig


class ParlerPatchConfig(AppConfig):
    name = "parler_patch"
    verbose_name = "Parler Compatibility Patch"

    def ready(self):
        # On applique le patch uniquement quand Django est prêt
        from .monkey import patch_parler

        patch_parler()
