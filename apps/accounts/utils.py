import secrets
import re
import requests
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone


# ========== VALIDATION FUNCTIONS ==========
def validate_ethiopian_phone(phone):
    """Validate Ethiopian phone number format (+251XXXXXXXXX)"""
    pattern = r'^\+?251[0-9]{9}$'
    return bool(re.match(pattern, phone.replace(' ', '')))


def validate_email_format(email):
    """Basic email format validation"""
    pattern = r'^[^@]+@[^@]+\.[^@]+$'
    return bool(re.match(pattern, email))


# ========== TOKEN GENERATION ==========
def generate_verification_token():
    """Generate a unique, secure token for verification"""
    return secrets.token_urlsafe(32)


def generate_user_number():
    """Generate unique user number: USR-YYYYMMDD-XXXX"""
    prefix = f"USR-{timezone.now().strftime('%Y%m%d')}"
    from .models import User
    count = User.objects.filter(user_number__startswith=prefix).count() + 1
    return f"{prefix}-{count:04d}"


# ========== CACHE MANAGEMENT ==========
def store_token(user_id, token, token_type, expiry_hours=24):
    """Store token in cache with expiry"""
    cache_key = f"{token_type}_{token}"
    cache.set(cache_key, {
        'user_id': str(user_id),
        'type': token_type,
        'expires_at': timezone.now() + timedelta(hours=expiry_hours)
    }, timeout=expiry_hours * 3600)
    return cache_key


def get_token_data(token, token_type):
    """Retrieve token data from cache"""
    cache_key = f"{token_type}_{token}"
    return cache.get(cache_key)


def delete_token(token, token_type):
    """Delete token from cache"""
    cache_key = f"{token_type}_{token}"
    cache.delete(cache_key)


# ========== EMAIL FUNCTIONS ==========
def send_verification_email(email, token, full_name):
    """Send verification link via email"""
    verification_link = f"{settings.FRONTEND_URL}/verify?token={token}&type=email"
    
    subject = 'Verify Your Email - Civic Issues Tracker'
    message = f"""
Hello {full_name},

Welcome to Civic Issues Tracker!

Please click the link below to verify your email address:

{verification_link}

This link expires in 24 hours.

If you didn't create an account, please ignore this email.

Thank you,
Civic Issues Tracker Team
"""
    
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        print(f"✅ Verification email sent to {email}")
        print(f"   Link: {verification_link}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def send_password_setup_email(email, token, full_name, organization_name):
    """Send password setup link for organization admins"""
    setup_link = f"{settings.FRONTEND_URL}/set-password?token={token}"
    
    subject = 'Complete Your Registration - Civic Issues Tracker'
    message = f"""
Hello {full_name},

You have been added as an Organization Admin for {organization_name}.

Please click the link below to set your password:

{setup_link}

This link expires in 7 days.

Thank you,
Civic Issues Tracker Team
"""
    
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        print(f"✅ Password setup email sent to {email}")
        print(f"   Link: {setup_link}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


# ========== TELEGRAM FUNCTIONS ==========

def generate_telegram_deep_link(token):
    """Generate a Telegram deep link"""
    bot_username = settings.TELEGRAM_BOT_USERNAME
    return f"https://t.me/{bot_username}?start=verify_{token}"


def send_telegram_message(chat_id, message):
    """Send a message via Telegram Bot using chat_id"""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json().get('ok', False)
    except:
        return False


def send_telegram_verification_button(phone_number, token, full_name):
    """Send verification button/link via Telegram using phone number"""
    if not settings.TELEGRAM_BOT_TOKEN:
        print("⚠️ Telegram bot token not configured")
        return False
    
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    deep_link = generate_telegram_deep_link(token)
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': phone_number,
        'text': f"🔐 <b>Verify Your Account</b>\n\nHello {full_name},\n\nClick the link below to start verification:\n\n{deep_link}\n\n⏰ This link expires in 24 hours.",
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            print(f"✅ Telegram message sent to {phone_number}")
            print(f"   Deep link: {deep_link}")
            return True
        else:
            error = result.get('description', 'Unknown error')
            print(f"❌ Telegram error: {error}")
            return False
    except Exception as e:
        print(f"❌ Telegram connection error: {e}")
        return False


def handle_telegram_start_command(token, chat_id, telegram_username=None):
    """Handle the /start verify_XXX command"""
    from .models import User
    
    token_data = get_token_data(token, 'telegram_pending')
    
    if not token_data:
        return "❌ Invalid or expired verification request."
    
    user_id = token_data['user_id']
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return "❌ User not found."
    
    # Store chat_id
    user.telegram_chat_id = str(chat_id)
    if telegram_username:
        user.telegram_username = telegram_username
    user.save()
    
    verification_token = generate_verification_token()
    store_token(user.id, verification_token, 'telegram')
    
    verification_link = f"{settings.FRONTEND_URL}/verify?token={verification_token}&type=telegram"
    
    return f"""
🔐 <b>Verify Your Account</b>

Hello <b>{user.full_name}</b>,

Click the link below to verify your account:

👉 <a href="{verification_link}">Verify Now</a>

⏰ This link expires in 24 hours.

—
<i>Civic Issues Tracker</i>
"""