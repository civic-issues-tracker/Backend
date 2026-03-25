from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Resident, Role
from .utils import (
    validate_ethiopian_phone,
    validate_email_format,
    generate_user_number,
    generate_verification_token,
    store_token,
    send_verification_email,
    generate_telegram_deep_link,
    send_telegram_verification_button,
)


class ResidentRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    verification_method = serializers.ChoiceField(choices=['email', 'telegram'], write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'phone', 'full_name', 'password', 'confirm_password',
            'verification_method'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        phone = data.get('phone')
        if not phone:
            raise serializers.ValidationError({"phone": "Phone number is required"})
        
        if not validate_ethiopian_phone(phone):
            raise serializers.ValidationError({"phone": "Invalid phone format. Use +251XXXXXXXXX"})
        
        email = data.get('email')
        if email and not validate_email_format(email):
            raise serializers.ValidationError({"email": "Invalid email format"})
        
        method = data.get('verification_method')
        if method == 'email' and not email:
            raise serializers.ValidationError({
                "verification_method": "Cannot verify via email because no email was provided"
            })
        
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        verification_method = validated_data.pop('verification_method')
        
        role = Role.objects.get(name='resident')
        user_number = generate_user_number()
        
        user = User.objects.create_user(
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            phone=validated_data['phone'],
            full_name=validated_data['full_name'],
            role=role,
            user_number=user_number,
            email_verified=False,
            telegram_verified=False
        )
        
        Resident.objects.create(user=user)
        
        token = generate_verification_token()
        
        if verification_method == 'email':
            store_token(user.id, token, 'email')
            send_verification_email(user.email, token, user.full_name)
            
        else:  # telegram
            store_token(user.id, token, 'telegram_pending')
            
            # Send button instead of deep link (better UX)
            send_telegram_verification_button(user.phone, token, user.full_name)
            
            print("\n" + "=" * 70)
            print("📱 TELEGRAM VERIFICATION BUTTON SENT")
            print("=" * 70)
            print(f"To: {user.phone}")
            print(f"Token: {token}")
            print("\nUser will receive a button in Telegram. They need to:")
            print("1. Open Telegram")
            print("2. Find the message from @CivicIssuesTrackerBot")
            print("3. Click the 'Start Verification' button")
            print("=" * 70)
            print("\n")
        
        return user


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
        
        if user.role.name == 'resident':
            if not (user.email_verified or user.telegram_verified):
                raise serializers.ValidationError("Account not verified. Please verify your account.")
        elif user.role.name == 'organization_admin':
            if not user.email_verified:
                raise serializers.ValidationError("Account not activated. Please check your email.")

        data['user'] = user
        return data


class VerifySerializer(serializers.Serializer):
    token = serializers.CharField()
    type = serializers.ChoiceField(choices=['email', 'telegram'])


class SetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data


class CompleteRegistrationSerializer(serializers.Serializer):
    """Serializer for organization admin completing registration"""
    token = serializers.CharField()
    full_name = serializers.CharField(max_length=100)
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
            'email_verified', 'telegram_verified', 'created_at'
        ]
        read_only_fields = ['id', 'user_number', 'created_at']


class CreateOrgAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    organization_id = serializers.UUIDField()