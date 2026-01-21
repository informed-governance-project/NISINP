from governanceplatform.helpers import set_creator


class ImportMixin:
    def get_import_data_kwargs(self, request, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(request, *args, **kwargs)
        cr = request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

    def save_model(self, request, obj, form, change):
        try:
            set_creator(request, obj, change)
        except Exception:
            pass
        super().save_model(request, obj, form, change)
