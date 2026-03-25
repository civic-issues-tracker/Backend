from rest_framework import permissions


class IsSystemAdmin(permissions.BasePermission):
    """
    Allows access only to users with system admin role
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role and 
            request.user.role.name == 'system_admin'
        )


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access only to users with organization admin role
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role and 
            request.user.role.name == 'organization_admin'
        )


class IsResident(permissions.BasePermission):
    """
    Allows access only to users with resident role
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role and 
            request.user.role.name == 'resident'
        )


class IsSystemAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for everyone, write only for system admins
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return IsSystemAdmin().has_permission(request, view)