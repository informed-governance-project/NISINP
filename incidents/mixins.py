class TranslationUpdateMixin:
    def after_save_instance(self, instance, using_transactions, dry_run):
        fields = instance._parler_meta.get_all_fields()
        defaults = {}
        for field in fields:
            field_value = getattr(instance, field)
            defaults[field] = field_value
        instance.translations.update_or_create(
            master_id=instance.id,
            language_code=instance.language_code,
            defaults=defaults,
        )
