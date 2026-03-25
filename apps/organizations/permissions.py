from rest_framework import permissions

class IsResident(permissions.BasePermission):
    """Allows access only to users with resident role"""
    def has_permission(self, request, view):
        return bool(request.user and 
                   request.user.is_authenticated and 
                   request.user.role and 
                   request.user.role.name == 'resident')


class IsOrgAdmin(permissions.BasePermission):
    """Allows access only to users with organization admin role"""
    def has_permission(self, request, view):
        return bool(request.user and 
                   request.user.is_authenticated and 
                   request.user.role and 
                   request.user.role.name == 'organization_admin')


class IsSystemAdmin(permissions.BasePermission):
    """Allows access only to users with system admin role"""
    def has_permission(self, request, view):
        return bool(request.user and 
                   request.user.is_authenticated and 
                   request.user.role and 
                   request.user.role.name == 'system_admin')


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission to only allow owners of an object to edit it"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user