from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Resident, OrganizationAdmin, SystemAdmin


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['full_name', 'email', 'phone', 'role', 'is_active', 'email_verified']
    list_filter = ['role', 'is_active', 'email_verified']
    search_fields = ['email', 'phone', 'full_name', 'user_number']
    
    # Use a field that ALWAYS exists: full_name or id or created_at
    ordering = ['full_name']  # This always exists
    
    fieldsets = (
        ('Personal Info', {'fields': ('user_number', 'full_name', 'email', 'phone')}),
        ('Permissions', {'fields': ('role', 'organization', 'is_active', 'is_staff', 'is_superuser')}),
        ('Verification', {'fields': ('email_verified', 'telegram_verified')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'full_name', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ['user_number', 'created_at', 'updated_at']


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__full_name', 'user__email', 'user__phone']


@admin.register(OrganizationAdmin)
class OrganizationAdminAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'created_at']
    search_fields = ['user__full_name', 'user__email', 'organization__name']


@admin.register(SystemAdmin)
class SystemAdminAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__full_name', 'user__email']