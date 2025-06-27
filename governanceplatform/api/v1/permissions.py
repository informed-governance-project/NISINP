from rest_framework.permissions import BasePermission, SAFE_METHODS


class GroupBasedModificationOrReadOnly(BasePermission):
    """
    GET HEAD OPTION for all authenticated user
    POST/PUT/PATCH/DELETE only for grouped passed in the view in the variable write_groups
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Get authorised group
        write_groups = getattr(view, 'write_groups', [])

        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name__in=write_groups).exists()
        )


class GroupBasedPermission(BasePermission):
    """
    GET HEAD OPTION for users in `read_groups`
    POST/PUT/PATCH/DELETE only for grouped passed in the view in the variable write_groups
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            allowed_read_groups = getattr(view, "read_groups", [])
            if not allowed_read_groups:
                return False
            return user.groups.filter(name__in=allowed_read_groups).exists()

        allowed_write_groups = getattr(view, "write_groups", [])
        if not allowed_write_groups:
            return False
        return user.groups.filter(name__in=allowed_write_groups).exists()


class IsRegulatorCreatorModificationOrReadOnly(BasePermission):
    """
    GET HEAD OPTION for all authenticated user
    POST/PUT/PATCH/DELETE only for the creator
    """

    def has_permission(self, request, view):
        # not allowed for unauthentified
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read for everyone
        if request.method in SAFE_METHODS:
            return True

        creator = obj.creator
        regulator = request.user.regulators.first()

        return creator == regulator


class CreatorAndActionGroupPermission(BasePermission):
    """
    Authorize DRF action depending on group defined on views
    Exemple : allowed_groups = {
        "list": ["OperatorUser", "OperatorAdmin"],
        "create": ["RegulatorAdmin"],
        "update": ["RegulatorAdmin"],
        "destroy": ["RegulatorAdmin", "is_creator"],
    }
    is_creator to filter on the object creator or not
    if an action is not present in allowed group, it's denied by default
    list	GET on /
    retrieve	GET on /<id>/
    create	POST
    update	PUT
    partial_update	PATCH
    destroy	DELETE
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        action = getattr(view, "action", None)
        allowed_groups = getattr(view, "allowed_groups", {})

        # refused if action is not defined
        if action not in allowed_groups:
            return False

        # Authorised if the user belong to at least one group
        return user.groups.filter(name__in=allowed_groups[action]).exists()

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action", None)
        allowed_groups = getattr(view, "allowed_groups", {})
        if action not in allowed_groups:
            return False

        if "is_creator" in allowed_groups[action]:
            creator = obj.creator
            regulator = request.user.regulators.first()

            return creator == regulator
        else:
            return True
