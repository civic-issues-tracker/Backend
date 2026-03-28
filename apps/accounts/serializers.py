from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import authenticate
from .models import User, Resident, Role
from .utils import (
    validate_ethiopian_phone,
    validate_email_format,
    generate_user_number,
)


class ResidentRegistrationSerializer(serializers.Serializer):
    """Serializer for resident registration (no user creation yet)"""
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=True)
    full_name = serializers.CharField(max_length=100, required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    confirm_password = serializers.CharField(write_only=True, min_length=8, required=True)
    verification_method = serializers.ChoiceField(choices=['email', 'sms'], write_only=True, required=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        # Phone is mandatory for residents
        phone = data.get('phone')
        if not phone:
            raise serializers.ValidationError({"phone": "Phone number is required"})
        
        if not validate_ethiopian_phone(phone):
            raise serializers.ValidationError({"phone": "Invalid phone format. Use +251XXXXXXXXX"})
        
        # Email is optional
        email = data.get('email')
        if email and not validate_email_format(email):
            raise serializers.ValidationError({"email": "Invalid email format"})
        
        method = data.get('verification_method')
        if method == 'email' and not email:
            raise serializers.ValidationError({
                "verification_method": "Cannot verify via email because no email was provided"
            })
        
        # Check if user already exists
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists"})
        
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": "A user with this phone number already exists"})
        
        return data


class VerifyOTPSerializer(serializers.Serializer):
    temp_id = serializers.CharField(required=True)
    otp_code = serializers.CharField(max_length=6, required=True)


class ResendOTPSerializer(serializers.Serializer):
    temp_id = serializers.CharField(required=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')

        if not (email or phone):
            raise serializers.ValidationError("Either email or phone is required")
        
        if not password:
            raise serializers.ValidationError("Password is required")

        user = None
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass
        
        if not user and phone:
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError("No account found with these credentials")
        
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")
        
        if not user.is_verified:
            raise serializers.ValidationError("Account not verified. Please verify your account first.")
        
        data['user'] = user
        return data


class CreateOrgAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    organization_id = serializers.UUIDField()

    def validate_email(self, value):
        # Check if email already exists
        from .models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value


class CompleteRegistrationSerializer(serializers.Serializer):
    token = serializers.CharField()
    full_name = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        # Password strength validation (optional)
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters"})
        
        # Check if password contains at least one number
        if not any(char.isdigit() for char in password):
            raise serializers.ValidationError({"password": "Password must contain at least one number"})
        
        return data


class SetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data


class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'user_number', 'email', 'phone', 'full_name', 'role_name',
            'email_verified', 'sms_verified', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'user_number', 'created_at']

class SystemAdminRegistrationSerializer(serializers.Serializer):
    """
    Serializer for creating the initial system admin (only one allowed)
    """
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20, required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    admin_secret_key = serializers.CharField(write_only=True)

    def validate(self, data):
        from .models import User
        
        # Check if passwords match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        # Check if system admin already exists
        if User.objects.filter(is_superuser=True).exists():
            raise serializers.ValidationError({
                "non_field_errors": ["System admin already exists. Only one system administrator is allowed."]
            })
        
        # Check if user already exists
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists"})
        
        if User.objects.filter(phone=data['phone']).exists():
            raise serializers.ValidationError({"phone": "User with this phone already exists"})
        
        # Check admin secret key
        admin_secret = data.get('admin_secret_key')
        expected_secret = getattr(settings, 'ADMIN_CREATION_SECRET', None)
        
        if not expected_secret:
            raise serializers.ValidationError({
                "admin_secret_key": "Admin creation is not configured. Please contact system administrator."
            })
        
        if admin_secret != expected_secret:
            raise serializers.ValidationError({"admin_secret_key": "Invalid admin secret key"})
        
        return data