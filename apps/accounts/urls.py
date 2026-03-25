from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Resident Registration
    path('register/resident/', views.ResidentRegisterView.as_view(), name='resident-register'),
    
    # Verification
    path('verify/', views.VerifyView.as_view(), name='verify'),
    
    # Login/Logout/Profile
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Organization Admin (System Admin only)
    path('admin/create-org-admin/', views.CreateOrganizationAdminView.as_view(), name='create-org-admin'),

    path('complete-registration/', views.CompleteRegistrationView.as_view(), name='complete-registration'),
    
    # Set Password (for Org Admins)
    path('set-password/', views.SetPasswordView.as_view(), name='set-password'),

    # ... existing URLs ...
    path('telegram-webhook/', views.telegram_webhook, name='telegram-webhook'),
]