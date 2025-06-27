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
