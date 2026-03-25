from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import json

from .serializers import (
    ResidentRegistrationSerializer,
    LoginSerializer,
    UserSerializer,
    VerifySerializer,
    SetPasswordSerializer,
    CreateOrgAdminSerializer,
    CompleteRegistrationSerializer,
)
from .models import Role, OrganizationAdmin
from .utils import (
    get_token_data, delete_token, send_password_setup_email,
    generate_verification_token, store_token, generate_user_number,
    handle_telegram_start_command, send_telegram_message,
    send_telegram_verification_button
)
from apps.organizations.models import Organization
from .models import User


class ResidentRegisterView(generics.CreateAPIView):
    serializer_class = ResidentRegistrationSerializer
    permission_classes = [AllowAny]


class VerifyView(generics.GenericAPIView):
    serializer_class = VerifySerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        verification_type = serializer.validated_data['type']
        
        token_data = get_token_data(token, verification_type)
        
        if not token_data:
            return Response(
                {"error": "Invalid or expired verification link"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=token_data['user_id'])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if verification_type == 'email':
            user.email_verified = True
        else:  # telegram
            user.telegram_verified = True
        
        user.save()
        delete_token(token, verification_type)
        
        return Response({
            "message": f"{verification_type.capitalize()} verified successfully!",
            "user": UserSerializer(user).data
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
                phone='',
                full_name='',
                role=role,
                user_number=user_number,
                email_verified=False
            )
            
            OrganizationAdmin.objects.create(
                user=user,
                organization=organization
            )
            
            token = generate_verification_token()
            store_token(user.id, token, 'registration_complete', expiry_hours=168)
            send_password_setup_email(email, token, '', organization.name)
        
        return Response({
            "message": f"Organization admin invitation sent to {email}. They will complete registration via email link."
        }, status=status.HTTP_201_CREATED)


class CompleteRegistrationView(generics.GenericAPIView):
    serializer_class = CompleteRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        full_name = serializer.validated_data['full_name']
        password = serializer.validated_data['password']
        
        token_data = get_token_data(token, 'registration_complete')
        
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
        user.email_verified = True
        user.save()
        
        delete_token(token, 'registration_complete')
        
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
        user.email_verified = True
        user.save()
        delete_token(token, 'password_setup')
        
        return Response({"message": "Password set successfully! You can now login."})


# ========== TELEGRAM WEBHOOK WITH SECURITY ==========

@csrf_exempt
def telegram_webhook(request):
    """
    Handle incoming Telegram messages with security checks
    Endpoint: POST /api/v1/auth/telegram-webhook/
    """
    print("\n" + "=" * 60)
    print("📨 Telegram webhook received!")
    print("=" * 60)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"Data: {json.dumps(data, indent=2)[:500]}...")
            
            # Handle callback queries (button clicks)
            callback_query = data.get('callback_query')
            if callback_query:
                return handle_telegram_callback(callback_query)
            
            # Handle regular messages
            message = data.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            telegram_username = message.get('chat', {}).get('username', '')
            
            print(f"Chat ID: {chat_id}")
            print(f"Username: {telegram_username}")
            print(f"Message: {text}")
            
            # Check if user clicked a deep link with /start verify_XXX
            if text.startswith('/start verify_'):
                token = text.replace('/start verify_', '')
                print(f"Token extracted: {token}")
                
                # Pass chat_id for security check
                response_text = handle_telegram_start_command(token, chat_id, telegram_username)
                print(f"Response: {response_text[:200]}...")
                
                # Send response back to user
                send_telegram_message(chat_id, response_text)
                print("✅ Response sent!")
            
            return JsonResponse({'ok': True})
            
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'ok': False}, status=500)
    
    return HttpResponse('Method not allowed', status=405)


def handle_telegram_callback(callback_query):
    """
    Handle inline keyboard button clicks
    """
    callback_data = callback_query.get('data', '')
    chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
    telegram_username = callback_query.get('from', {}).get('username', '')
    
    print(f"📱 Callback received: {callback_data}")
    print(f"Chat ID: {chat_id}")
    print(f"Username: {telegram_username}")
    
    if callback_data.startswith('start_verify_'):
        token = callback_data.replace('start_verify_', '')
        print(f"Token: {token}")
        
        response_text = handle_telegram_start_command(token, chat_id, telegram_username)
        send_telegram_message(chat_id, response_text)
        
        # Answer callback query to remove loading state
        answer_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, json={'callback_query_id': callback_query.get('id'), 'text': 'Processing...'})
    
    return JsonResponse({'ok': True})