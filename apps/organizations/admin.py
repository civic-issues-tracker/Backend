from django.contrib import admin
from .models import Organization, Category, SubCategory, CategoryOrganization


class CategoryOrganizationInline(admin.TabularInline):
    """Inline admin for Category-Organization relationships"""
    model = CategoryOrganization
    extra = 1
    autocomplete_fields = ['organization']
    fields = ['organization', 'is_active']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_email', 'contact_phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_email']
    ordering = ['name']
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = "Activate selected organizations"
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = "Deactivate selected organizations"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['get_name_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    inlines = [CategoryOrganizationInline]
    filter_horizontal = ['organizations']


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name']
    ordering = ['category', 'name']


@admin.register(CategoryOrganization)
class CategoryOrganizationAdmin(admin.ModelAdmin):
    list_display = ['category', 'organization', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['category__name', 'organization__name']