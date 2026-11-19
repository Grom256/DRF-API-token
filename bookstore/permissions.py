from rest_framework import permissions


class IsOwnerOrModeratorOrReadOnly(permissions.BasePermission):
    """
    P3: Читання — всім.
    Створити — будь-який автентифікований.
    Змінити чи видалити — лише власник книги або член групи Moderators.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            obj.owner == request.user
            or request.user.groups.filter(name="Moderators").exists()
        )
