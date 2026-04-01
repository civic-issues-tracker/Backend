from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import json
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings

from .serializers import (
    ResidentRegistrationSerializer,
    LoginSerializer,
    UserSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    CreateOrgAdminSerializer,
    CompleteRegistrationSerializer,
    SetPasswordSerializer,
    SystemAdminRegistrationSerializer,  
    ForgotPasswordSerializer,      
    ResetPasswordSerializer,
)
from .models import Role, OrganizationAdmin, User
from .utils import (
    generate_user_number,
    send_password_setup_email,
    generate_verification_token,
    store_token,
    get_token_data,
    delete_token,
)
from .otp_service import OTPService
from apps.organizations.models import Organization


class ResidentRegisterView(generics.GenericAPIView):
    serializer_class = ResidentRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        verification_method = validated_data.pop('verification_method')
        validated_data.pop('confirm_password')
        
        # Check if user already exists in database
        phone = validated_data.get('phone')
        email = validated_data.get('email')
        
        if User.objects.filter(phone=phone).exists():
            return Response(
                {"error": "A user with this phone number already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if email and User.objects.filter(email=email).exists():
            return Response(
                {"error": "A user with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there's already a pending registration for this contact
        contact = validated_data.get('email', validated_data.get('phone'))
        has_pending, existing_temp_id, pending_data = OTPService.check_existing_pending(contact)
        
        if has_pending:
            # If pending exists, resend OTP with existing temp_id
            temp_id = existing_temp_id
            otp_code = pending_data['otp_code']
            
            # Resend OTP
            if verification_method == 'email':
                success, message = OTPService.send_email_otp(
                    validated_data['email'], 
                    otp_code, 
                    validated_data['full_name']
                )
            else:
                success, message = OTPService.send_sms(
                    validated_data['phone'], 
                    otp_code
                )
            
            if not success:
                return Response(
                    {"error": f"Failed to send OTP: {message}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                "message": f"A pending registration exists. New OTP sent to your {verification_method}.",
                "temp_id": temp_id,
                "verification_method": verification_method,
                "expires_in": 20
            }, status=status.HTTP_200_OK)
        
        # Store registration data in cache with OTP
        temp_id, otp_code = OTPService.store_pending_user(validated_data, verification_method)
        
        # Send OTP
        if verification_method == 'email':
            success, message = OTPService.send_email_otp(
                validated_data['email'], 
                otp_code, 
                validated_data['full_name']
            )
        else:  # sms
            success, message = OTPService.send_sms(
                validated_data['phone'], 
                otp_code
            )
        
        if not success:
            OTPService.delete_pending_user(temp_id)
            return Response(
                {"error": f"Failed to send {verification_method} OTP: {message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            "message": f"OTP sent to your {verification_method}. Please verify to complete registration.",
            "temp_id": temp_id,
            "verification_method": verification_method,
            "expires_in": 20
        }, status=status.HTTP_201_CREATED)

        
class VerifyOTPView(generics.GenericAPIView):
    """
    Step 2: Verify OTP and create the actual user
    """
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        temp_id = serializer.validated_data['temp_id']
        otp_code = serializer.validated_data['otp_code']
        
        # Verify OTP and create user
        success, message, user = OTPService.verify_otp_and_create_user(temp_id, otp_code)
        
        if not success:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": message,
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class ResendOTPView(generics.GenericAPIView):
    """
    Resend OTP for pending registration
    """
    serializer_class = ResendOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        temp_id = serializer.validated_data['temp_id']
        
        # Get pending user data
        pending_data = OTPService.get_pending_user(temp_id)
        
        if not pending_data:
            return Response(
                {"error": "Registration session expired. Please register again."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if too many resend attempts
        resend_count = pending_data.get('resend_count', 0)
        if resend_count >= 3:
            OTPService.delete_pending_user(temp_id)
            return Response(
                {"error": "Too many resend attempts. Please register again."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new OTP
        new_otp = OTPService.generate_otp()
        pending_data['otp_code'] = new_otp
        pending_data['attempts'] = 0
        pending_data['resend_count'] = resend_count + 1
        
        # Update cache
        cache_key = f"pending_user_{temp_id}"
        from django.core.cache import cache
        cache.set(cache_key, pending_data, timeout=1200)
        
        # Resend OTP
        registration_data = pending_data['registration_data']
        method = pending_data['method']
        
        if method == 'email':
            success, message = OTPService.send_email_otp(
                registration_data['email'],
                new_otp,
                registration_data['full_name']
            )
        else:
            success, message = OTPService.send_sms(
                registration_data['phone'],
                new_otp
            )
        
        if not success:
            return Response(
                {"error": f"Failed to send OTP: {message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            "message": f"New OTP sent to your {method}",
            "temp_id": temp_id
        })


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({"message": "Successfully logged out"})
            return Response(
                {"error": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CreateSystemAdminView(generics.GenericAPIView):
    """
    Create the initial system admin (only one allowed)
    This endpoint can only be called once during initial setup
    """
    serializer_class = SystemAdminRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        from .models import User
        
        if User.objects.filter(is_superuser=True).exists():
            return Response(
                {
                    "error": "System admin already exists. Only one system administrator is allowed in the system.",
                    "message": "If you need additional administrators, create them as Organization Admins."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        
        with transaction.atomic():
            from .models import Role, SystemAdmin
            from .utils import generate_user_number
            
            role = Role.objects.get(name='system_admin')
            user_number = generate_user_number()
            
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                phone=validated_data['phone'],
                full_name=validated_data['full_name'],
                role=role,
                user_number=user_number,
                is_verified=True,
                is_active=True,
                email_verified=True,
                is_staff=True,
                is_superuser=True
            )
            
            SystemAdmin.objects.create(user=user)
            
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "System admin created successfully! Only one system admin is allowed in the system.",
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }, status=status.HTTP_201_CREATED)
        

class CreateOrganizationAdminView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role.name != 'system_admin':
            return Response(
                {"error": "Only system admins can create organization admins"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateOrgAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        organization_id = serializer.validated_data['organization_id']
        
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        with transaction.atomic():
            role = Role.objects.get(name='organization_admin')
            user_number = generate_user_number()
            
            user = User.objects.create_user(
                email=email,
                password=None,
                phone=None,
                full_name='',
                role=role,
                user_number=user_number,
                is_verified=False,
                is_active=False,
                email_verified=False
            )
            
            OrganizationAdmin.objects.create(
                user=user,
                organization=organization
            )
            
            token = generate_verification_token()
            store_token(user.id, token, 'org_admin_setup', expiry_hours=168)
            send_password_setup_email(email, token, '', organization.name)
        
        return Response({
            "message": f"Organization admin invitation sent to {email}. They will complete registration via email link."
        }, status=status.HTTP_201_CREATED)


class CompleteRegistrationView(generics.GenericAPIView):
    """Complete registration for organization admin"""
    serializer_class = CompleteRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        full_name = serializer.validated_data['full_name']
        password = serializer.validated_data['password']
        
        token_data = get_token_data(token, 'org_admin_setup')
        
        if not token_data:
            return Response(
                {"error": "Invalid or expired registration link"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=token_data['user_id'])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.full_name = full_name
        user.set_password(password)
        user.is_active = True
        user.is_verified = True
        user.email_verified = True
        user.save()
        
        delete_token(token, 'org_admin_setup')
        
        return Response(
            {"message": "Registration complete! You can now login."},
            status=status.HTTP_200_OK
        )


class SetPasswordView(generics.GenericAPIView):
    serializer_class = SetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        
        token_data = get_token_data(token, 'password_setup')
        
        if not token_data:
            return Response(
                {"error": "Invalid or expired password setup link"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=token_data['user_id'])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.set_password(password)
        user.is_active = True
        user.is_verified = True
        user.email_verified = True
        user.save()
        delete_token(token, 'password_setup')
        
        return Response({"message": "Password set successfully! You can now login."})
    
class SystemAdminStatusView(generics.GenericAPIView):
    """Check if system admin has been created"""
    permission_classes = [AllowAny]

    def get(self, request):
        has_admin = User.objects.filter(is_superuser=True).exists()
        return Response({
            "system_admin_exists": has_admin,
            "message": "System admin exists" if has_admin else "No system admin found. Please create one using the registration endpoint."
        })


class ForgotPasswordView(generics.GenericAPIView):
    """
    Step 1: Request password reset
    User provides email or phone, system sends reset instructions
    """
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        from django.core.cache import cache
        from django.core.mail import send_mail
        from django.utils import timezone
        from datetime import timedelta
        from .otp_service import OTPService
        from .utils import generate_verification_token, store_token
        
        print("=" * 60)
        print("FORGOT PASSWORD REQUEST")
        print("=" * 60)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        contact_method = validated_data['contact_method']
        contact_value = validated_data['contact_value']
        
        print(f"Contact method: {contact_method}")
        print(f"Contact value: {contact_value}")
        
        # Find user
        user = None
        if contact_method == 'email':
            try:
                user = User.objects.get(email=contact_value)
                print(f"✅ Found user by email: {user.email}")
            except User.DoesNotExist:
                print(f"❌ No user found for email: {contact_value}")
                pass
        else:
            try:
                user = User.objects.get(phone=contact_value)
                print(f"✅ Found user by phone: {user.phone}")
            except User.DoesNotExist:
                print(f"❌ No user found for phone: {contact_value}")
                pass
        
        if not user:
            print("User not found - returning success message")
            return Response({
                "message": "If your account exists, you will receive reset instructions."
            }, status=status.HTTP_200_OK)
        
        # Rate limiting
        rate_limit_key = f"reset_rate_limit_{contact_value}"
        attempts = cache.get(rate_limit_key, 0)
        print(f"Rate limit attempts: {attempts}")
        
        if attempts >= 3:
            print("Rate limit exceeded")
            return Response({
                "error": "Too many reset requests. Please try again later."
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        cache.set(rate_limit_key, attempts + 1, timeout=3600)
        print(f"Rate limit incremented to {attempts + 1}")
        
        # Generate token
        token = generate_verification_token()
        print(f"🔑 GENERATED TOKEN: {token}")
        
        # Store token
        store_token(user.id, token, 'password_reset', expiry_hours=1)
        print(f"✅ Token stored with key: password_reset_{token}")
        
        # Send instructions based on contact method
        if contact_method == 'email':
            # EMAIL FLOW - Send reset link
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f"{frontend_url}/reset-password?token={token}"
            print(f"📧 Reset link: {reset_link}")
            
            subject = 'Reset Your Password - Civic Issues Tracker'
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; 
                              color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                    .footer {{ font-size: 12px; color: #777; text-align: center; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Civic Issues Tracker</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{user.full_name}</strong>,</p>
                        <p>We received a request to reset your password.</p>
                        <p>Click the button below to create a new password:</p>
                        <p style="text-align: center;">
                            <a href="{reset_link}" class="button">Reset Password</a>
                        </p>
                        <p>Or copy and paste this link: {reset_link}</p>
                        <p>This link will expire in <strong>1 hour</strong>.</p>
                        <p>If you didn't request this, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>Civic Issues Tracker - Improving community services</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            plain_message = f"""
Hello {user.full_name},

We received a request to reset your password.

Click the link below to create a new password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Civic Issues Tracker Team
"""
            
            try:
                print(f"📧 Attempting to send email to: {contact_value}")
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [contact_value],
                    fail_silently=False,
                    html_message=html_message
                )
                print(f"✅✅✅ EMAIL SENT SUCCESSFULLY to {contact_value} ✅✅✅")
            except Exception as e:
                print(f"❌❌❌ EMAIL FAILED: {e} ❌❌❌")
                import traceback
                traceback.print_exc()
                
        else:  # SMS flow
            otp_code = OTPService.generate_otp()
            print(f"📱 GENERATED OTP: {otp_code}")
            
            # Update token with OTP
            cache_key = f"password_reset_{token}"
            token_data = cache.get(cache_key)
            if token_data:
                token_data['otp_code'] = otp_code
                token_data['attempts'] = 0
                cache.set(cache_key, token_data, timeout=3600)
                print(f"✅ OTP added to token data")
            
            # Send SMS
            success, message = OTPService.send_sms(contact_value, otp_code)
            if success:
                print(f"✅ SMS sent to {contact_value}")
            else:
                print(f"❌ SMS failed: {message}")
        
        print("=" * 60)
        print("RETURNING SUCCESS RESPONSE")
        print("=" * 60)
        
        return Response({
            "message": "If your account exists, you will receive reset instructions."
        }, status=status.HTTP_200_OK)


class ResetPasswordView(generics.GenericAPIView):
    """
    Step 2: Execute password reset with token
    User provides token and new password
    """
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['password']
        
        # Get token data from cache
        from .utils import get_token_data
        token_data = get_token_data(token, 'password_reset')
        
        if not token_data:
            return Response({
                "error": "Invalid or expired reset token. Please request a new one."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if this is an OTP-based reset (SMS)
        if 'otp_code' in token_data:
            return Response({
                "error": "Please verify your code first using the verify-reset-otp endpoint."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user
        try:
            user = User.objects.get(id=token_data['user_id'])
        except User.DoesNotExist:
            return Response({
                "error": "User not found."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        # Delete token to prevent reuse
        from .utils import delete_token
        delete_token(token, 'password_reset')
        
        return Response({
            "message": "Password reset successful. You can now login with your new password."
        }, status=status.HTTP_200_OK)


class VerifyResetOTPView(generics.GenericAPIView):
    """
    For SMS-based password reset: Verify OTP then reset password
    """
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        from django.core.cache import cache
        from .utils import get_token_data, delete_token
        
        temp_id = request.data.get('temp_id')
        otp_code = request.data.get('otp_code')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        # Get token data from cache
        token_data = get_token_data(temp_id, 'password_reset')
        
        if not token_data:
            return Response({
                "error": "Invalid or expired reset session."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify OTP
        if token_data.get('otp_code') != otp_code:
            attempts = token_data.get('attempts', 0) + 1
            token_data['attempts'] = attempts
            cache_key = f"password_reset_{temp_id}"
            cache.set(cache_key, token_data, timeout=3600)
            
            if attempts >= 3:
                delete_token(temp_id, 'password_reset')
                return Response({
                    "error": "Too many failed attempts. Please request a new reset."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "error": f"Invalid code. {3 - attempts} attempts remaining."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate passwords
        if new_password != confirm_password:
            return Response({
                "error": "Passwords do not match."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user
        try:
            user = User.objects.get(id=token_data['user_id'])
        except User.DoesNotExist:
            return Response({
                "error": "User not found."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        # Delete token
        delete_token(temp_id, 'password_reset')
        
        return Response({
            "message": "Password reset successful. You can now login."
        }, status=status.HTTP_200_OK)