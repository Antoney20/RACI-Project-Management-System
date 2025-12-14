from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permission to only allow admin users to perform actions.
    """
    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsAdminOrSupervisor(permissions.BasePermission):
    """
    Permission to allow admin and supervisor users.
    """
    message = "Only administrators or supervisors can perform this action."

    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and (request.user.is_admin() or request.user.is_supervisor())
        )


class CanManageUser(permissions.BasePermission):
    """
    Permission to check if user can manage another user.
    - Admins can manage everyone
    - Supervisors can manage users they created
    - Users can only view/edit their own profile
    """
    message = "You don't have permission to manage this user."

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admins can do anything
        if user.is_admin():
            return True

        # Supervisors can manage users they created
        if user.is_supervisor():
            if view.action in ['retrieve', 'update', 'partial_update']:
                return obj.created_by == user or obj == user
            return False

        # Regular users can only view/edit themselves
        if view.action in ['retrieve', 'update', 'partial_update']:
            return obj == user

        return False