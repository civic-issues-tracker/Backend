from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Resident, OrganizationAdmin, SystemAdmin


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Use the fields that exist in your User model
    list_display = ['id', 'full_name', 'email', 'phone', 'role', 'is_active', 'is_verified', 'is_superuser']
    list_filter = ['role', 'is_active', 'is_verified', 'is_superuser', 'email_verified', 'sms_verified']
    search_fields = ['email', 'phone', 'full_name', 'user_number']
    
    # Order by a field that exists (full_name, email, or created_at)
    ordering = ['full_name']
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('user_number', 'full_name', 'email', 'phone')
        }),
        ('Permissions', {
            'fields': ('role', 'organization', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Verification', {
            'fields': ('is_verified', 'email_verified', 'sms_verified')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'full_name', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ['id', 'user_number', 'created_at', 'updated_at']
    
    # Override get_fieldsets to handle add form
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at']
    search_fields = ['user__full_name', 'user__email', 'user__phone']
    readonly_fields = ['id', 'created_at']


@admin.register(OrganizationAdmin)
class OrganizationAdminAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'organization', 'created_at']
    search_fields = ['user__full_name', 'user__email', 'organization__name']
    list_filter = ['organization']
    readonly_fields = ['id', 'created_at']


@admin.register(SystemAdmin)
class SystemAdminAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at']
    search_fields = ['user__full_name', 'user__email']
    readonly_fields = ['id', 'created_at']