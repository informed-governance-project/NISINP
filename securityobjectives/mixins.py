from governanceplatform.helpers import set_creator


class ImportMixin:
    def get_import_data_kwargs(self, request, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(request, *args, **kwargs)
        cr = request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)

    def get_model_perms(self, request):
        user = request.user
        functionalities = None
        if user.regulators.first() is not None:
            functionalities = user.regulators.first().functionalities
        if user.observers.first() is not None:
            functionalities = user.observers.first().functionalities
        if functionalities is not None:
            if "securityobjectives" in functionalities.all().values_list(
                "type", flat=True
            ):
                return {"change": True, "add": True}
        return {"change": False, "add": False}
