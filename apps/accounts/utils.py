import secrets
import re
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
    from .models import User
    prefix = f"USR-{timezone.now().strftime('%Y%m%d')}"
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
def send_password_setup_email(email, token, full_name, organization_name):
    """Send password setup link for organization admins"""
    # Frontend URL where they'll complete registration
    frontend_url = settings.FRONTEND_URL
    setup_link = f"{frontend_url}/complete-registration?token={token}"
    
    subject = f'Invitation to join {organization_name} - Civic Issues Tracker'
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; 
                      color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
            .footer {{ font-size: 12px; color: #777; text-align: center; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Civic Issues Tracker</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>You have been invited to join <strong>{organization_name}</strong> as an Organization Administrator.</p>
                <p>Please click the button below to complete your registration and set up your password:</p>
                <p style="text-align: center;">
                    <a href="{setup_link}" class="button">Complete Registration</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p><a href="{setup_link}">{setup_link}</a></p>
                <p><strong>Note:</strong> This invitation link will expire in 7 days.</p>
                <p>If you did not expect this invitation, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>Civic Issues Tracker - Improving community services</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_message = f"""
    Welcome to Civic Issues Tracker!
    
    You have been invited to join {organization_name} as an Organization Administrator.
    
    Please click the link below to complete your registration and set up your password:
    
    {setup_link}
    
    This invitation link will expire in 7 days.
    
    If you did not expect this invitation, please ignore this email.
    
    Civic Issues Tracker Team
    """
    
    try:
        send_mail(
            subject, 
            plain_message, 
            settings.DEFAULT_FROM_EMAIL, 
            [email], 
            fail_silently=False,
            html_message=html_message
        )
        print(f"✅ Invitation email sent to {email}")
        print(f"   Link: {setup_link}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False