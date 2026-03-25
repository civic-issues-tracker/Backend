from django.urls import path
from . import views

urlpatterns = [
    # Organization endpoints
    path('organizations/', views.OrganizationListCreateView.as_view(), name='organization-list'),
    path('organizations/inactive/', views.InactiveOrganizationsListView.as_view(), name='organization-inactive'),
    path('organizations/<uuid:pk>/', views.OrganizationDetailView.as_view(), name='organization-detail'),
    path('organizations/<uuid:pk>/activate/', views.OrganizationActivateView.as_view(), name='organization-activate'),
    
    # Category endpoints
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list'),
    path('categories/inactive/', views.InactiveCategoriesListView.as_view(), name='category-inactive'),
    path('categories/<uuid:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<uuid:pk>/activate/', views.CategoryActivateView.as_view(), name='category-activate'),
    
    # Category-Organization relationship endpoints
    path('categories/<uuid:category_id>/organizations/', 
         views.CategoryOrganizationsView.as_view(), 
         name='category-organizations'),
    path('categories/<uuid:category_id>/organizations/<uuid:organization_id>/', 
         views.CategoryOrganizationsView.as_view(), 
         name='category-organization-delete'),
    
    # SubCategory endpoints
    path('subcategories/', views.SubCategoryListCreateView.as_view(), name='subcategory-list'),
    path('subcategories/inactive/', views.InactiveSubCategoriesListView.as_view(), name='subcategory-inactive'),
    path('subcategories/<uuid:pk>/', views.SubCategoryDetailView.as_view(), name='subcategory-detail'),
    path('subcategories/<uuid:pk>/activate/', views.SubCategoryActivateView.as_view(), name='subcategory-activate'),
]