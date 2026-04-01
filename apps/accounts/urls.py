# apps/accounts/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Resident Registration (OTP flow)
    path('register/resident/', views.ResidentRegisterView.as_view(), name='resident-register'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),

    # System Admin Registration (One-time only)
    path('register/system-admin/', views.CreateSystemAdminView.as_view(), name='register-system-admin'),
    path('system-admin-status/', views.SystemAdminStatusView.as_view(), name='system-admin-status'),

    
    # Login/Logout/Profile
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),


    # Password Reset
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    path('verify-reset-otp/', views.VerifyResetOTPView.as_view(), name='verify-reset-otp'),
    
    # Organization Admin (System Admin only)
    path('admin/create-org-admin/', views.CreateOrganizationAdminView.as_view(), name='create-org-admin'),
    path('complete-registration/', views.CompleteRegistrationView.as_view(), name='complete-registration'),
    path('set-password/', views.SetPasswordView.as_view(), name='set-password'),
]