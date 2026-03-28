from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Organization, Category, SubCategory, CategoryOrganization
from .serializers import (
    OrganizationSerializer,
    CategorySerializer,
    CategoryDetailSerializer,
    SubCategorySerializer
)
from apps.common.permissions import IsSystemAdmin


# ========== ORGANIZATION VIEWS ==========

class OrganizationListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/organizations/ - List all active organizations
    POST /api/v1/organizations/ - Create new organization (System Admin only)
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSystemAdmin()]
        return [IsAuthenticated()]


class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/v1/organizations/{id}/ - Get organization details
    PUT /api/v1/organizations/{id}/ - Update organization (System Admin only)
    DELETE /api/v1/organizations/{id}/ - Soft delete organization (System Admin only)
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete ONLY the organization.
        Category links are removed, but categories themselves remain.
        """
        organization = self.get_object()
        
        # Count how many links will be removed (for feedback)
        link_count = organization.category_organizations.filter(is_active=True).count()
        
        # Remove all category links (hard delete the links - they're just relationships)
        organization.category_organizations.all().delete()
        
        # Soft delete only the organization
        organization.soft_delete()
        
        message = f"Organization '{organization.name}' has been deactivated."
        if link_count > 0:
            message += f" {link_count} category link(s) were removed. Categories themselves remain."
        
        return Response(
            {"message": message, "removed_links": link_count},
            status=status.HTTP_200_OK
        )


class OrganizationActivateView(generics.GenericAPIView):
    """
    POST /api/v1/organizations/{id}/activate/ - Activate a deactivated organization (System Admin only)
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, pk):
        organization = get_object_or_404(Organization.all_objects, id=pk, is_active=False)
        
        # Activate the organization
        organization.activate()
        
        # Note: Links are NOT restored automatically
        # Admin needs to re-link categories if needed
        
        return Response(
            {"message": f"Organization '{organization.name}' has been activated. Note: Category links were not restored."},
            status=status.HTTP_200_OK
        )


class InactiveOrganizationsListView(generics.ListAPIView):
    """
    GET /api/v1/organizations/inactive/ - List all inactive organizations (System Admin only)
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    serializer_class = OrganizationSerializer
    
    def get_queryset(self):
        return Organization.all_objects.filter(is_active=False)


# ========== CATEGORY VIEWS ==========

class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/categories/ - List all active categories
    POST /api/v1/categories/ - Create new category (System Admin only)
    """
    queryset = Category.objects.annotate(
        total_issues=Count('issues', filter=Q(issues__is_active=True))
    )
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CategoryDetailSerializer
        return CategorySerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSystemAdmin()]
        return [IsAuthenticated()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/v1/categories/{id}/ - Get category details
    PUT /api/v1/categories/{id}/ - Update category (System Admin only)
    DELETE /api/v1/categories/{id}/ - Soft delete category (System Admin only)
    """
    queryset = Category.objects.annotate(
        total_issues=Count('issues', filter=Q(issues__is_active=True))
    )
    
    def get_serializer_class(self):
        return CategoryDetailSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete ONLY the category.
        - Subcategories are NOT deleted
        - Organization links are removed
        """
        category = self.get_object()
        
        # Check if category has active issues
        active_issues_count = category.issues.filter(is_active=True).count()
        
        if active_issues_count > 0:
            return Response(
                {"error": f"Cannot deactivate category with {active_issues_count} active issues. Resolve or reassign issues first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Count subcategories (for feedback)
        subcategory_count = category.subcategories.filter(is_active=True).count()
        
        # Remove all organization links (hard delete - relationships only)
        category.category_organizations.all().delete()
        
        # Soft delete ONLY the category
        category.soft_delete()
        
        message = f"Category '{category.name}' has been deactivated."
        if subcategory_count > 0:
            message += f" {subcategory_count} subcategory(s) remain active and can still be used."
        
        return Response(
            {"message": message, "remaining_subcategories": subcategory_count},
            status=status.HTTP_200_OK
        )


class CategoryActivateView(generics.GenericAPIView):
    """
    POST /api/v1/categories/{id}/activate/ - Activate a deactivated category (System Admin only)
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, pk):
        category = get_object_or_404(Category.all_objects, id=pk, is_active=False)
        
        # Activate the category
        category.activate()
        
        # Note: Subcategories and organization links are NOT restored automatically
        return Response(
            {"message": f"Category '{category.get_name_display()}' has been activated. Subcategories remain active if they were active."},
            status=status.HTTP_200_OK
        )


class InactiveCategoriesListView(generics.ListAPIView):
    """
    GET /api/v1/categories/inactive/ - List all inactive categories (System Admin only)
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    serializer_class = CategorySerializer
    
    def get_queryset(self):
        return Category.all_objects.filter(is_active=False).annotate(
            total_issues=Count('issues', filter=Q(issues__is_active=True))
        )


# ========== CATEGORY ORGANIZATIONS VIEWS ==========

class CategoryOrganizationsView(generics.GenericAPIView):
    """
    GET /api/v1/categories/{id}/organizations/ - Get organizations for a category
    POST /api/v1/categories/{id}/organizations/ - Add organization to category (System Admin only)
    DELETE /api/v1/categories/{id}/organizations/{org_id}/ - Remove organization from category
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, category_id):
        """Get all active organizations linked to this category"""
        category = get_object_or_404(Category, id=category_id)
        organizations = category.organizations.filter(is_active=True)
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)
    
    def post(self, request, category_id):
        """Link an organization to this category"""
        if not IsSystemAdmin().has_permission(request, self):
            return Response(
                {"error": "Only system admins can add organizations to categories"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category = get_object_or_404(Category, id=category_id)
        organization_id = request.data.get('organization_id')
        
        if not organization_id:
            return Response(
                {"error": "organization_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        organization = get_object_or_404(Organization, id=organization_id)
        
        # Check if already linked
        if CategoryOrganization.objects.filter(
            category=category, 
            organization=organization
        ).exists():
            return Response(
                {"error": "Organization already linked to this category"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        CategoryOrganization.objects.create(category=category, organization=organization)
        
        return Response(
            {"message": f"Organization '{organization.name}' added to category '{category.name}'"},
            status=status.HTTP_201_CREATED
        )
    
    def delete(self, request, category_id, organization_id):
        """Remove an organization from a category"""
        if not IsSystemAdmin().has_permission(request, self):
            return Response(
                {"error": "Only system admins can remove organizations from categories"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category = get_object_or_404(Category, id=category_id)
        organization = get_object_or_404(Organization, id=organization_id)
        
        link = CategoryOrganization.objects.filter(
            category=category, 
            organization=organization
        ).first()
        
        if not link:
            return Response(
                {"error": "Organization not linked to this category"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        link.delete()  # Hard delete - it's just a relationship
        
        return Response(
            {"message": f"Organization '{organization.name}' removed from category '{category.name}'"},
            status=status.HTTP_200_OK
        )


# ========== SUBCATEGORY VIEWS ==========

class SubCategoryListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/subcategories/ - List all active subcategories
    POST /api/v1/subcategories/ - Create new subcategory (System Admin only)
    """
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSystemAdmin()]
        return [IsAuthenticated()]


class SubCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/v1/subcategories/{id}/ - Get subcategory details
    PUT /api/v1/subcategories/{id}/ - Update subcategory (System Admin only)
    DELETE /api/v1/subcategories/{id}/ - Soft delete subcategory (System Admin only)
    """
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete ONLY the subcategory.
        Nothing else is affected.
        """
        subcategory = self.get_object()
        
        # Check if subcategory has active issues
        if subcategory.issues.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot deactivate subcategory with existing active issues."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete only the subcategory
        subcategory.soft_delete()
        
        return Response(
            {"message": f"Subcategory '{subcategory.name}' has been deactivated."},
            status=status.HTTP_200_OK
        )


class SubCategoryActivateView(generics.GenericAPIView):
    """
    POST /api/v1/subcategories/{id}/activate/ - Activate a deactivated subcategory (System Admin only)
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, pk):
        subcategory = get_object_or_404(SubCategory.all_objects, id=pk, is_active=False)
        subcategory.activate()
        return Response(
            {"message": f"Subcategory '{subcategory.name}' has been activated."},
            status=status.HTTP_200_OK
        )


class InactiveSubCategoriesListView(generics.ListAPIView):
    """
    GET /api/v1/subcategories/inactive/ - List all inactive subcategories (System Admin only)
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    serializer_class = SubCategorySerializer
    
    def get_queryset(self):
        return SubCategory.all_objects.filter(is_active=False)



      