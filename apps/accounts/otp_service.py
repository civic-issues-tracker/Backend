import random
import requests
import uuid
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


class OTPService:
    """Handle OTP generation, sending, and verification with temporary user data storage"""
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def send_sms(phone_number, otp_code):
        """Send OTP via Afro Message API"""
        
        # Clean phone number (remove + if present)
        clean_number = phone_number.replace('+', '')
        
        # Get API configuration
        api_key = getattr(settings, 'AFRO_MESSAGE_API_KEY', None)
        api_url = getattr(settings, 'AFRO_MESSAGE_API_URL', 'https://api.afromessage.com/api/send')
        
        # Development mode - no API key
        if not api_key:
            print("\n" + "=" * 60)
            print("📱 SMS VERIFICATION (Development Mode)")
            print("=" * 60)
            print(f"To: {phone_number}")
            print(f"OTP: {otp_code}")
            print("=" * 60)
            return True, "OTP printed to console (development mode)"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Working payload format (no "from" field - let API use default)
        payload = {
            "to": clean_number,
            "message": f"Your Civic Issues Tracker verification code is: {otp_code}"
        }
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                if result.get('acknowledge') == 'success':
                    print(f"✅ SMS sent to {phone_number}")
                    return True, result
                else:
                    # Check if it's an unverified contact error
                    errors = result.get('response', {}).get('errors', [])
                    error_msg = str(errors[0]) if errors else 'Unknown error'
                    
                    if "unverified" in error_msg.lower():
                        print(f"⚠️ Contact {phone_number} not verified in Afro Message dashboard")
                        return False, "Contact not verified. Please verify this number in Afro Message dashboard."
                    else:
                        print(f"❌ SMS failed: {error_msg}")
                        return False, error_msg
            else:
                print(f"❌ SMS failed: HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            print("❌ SMS timeout")
            return False, "Timeout"
        except requests.exceptions.ConnectionError:
            print("❌ Connection error")
            return False, "Connection error"
        except Exception as e:
            print(f"❌ SMS error: {e}")
            return False, str(e)
    
    @staticmethod
    def send_email_otp(email, otp_code, full_name):
        """Send OTP via email"""
        subject = 'Your Verification Code - Civic Issues Tracker'
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #4CAF50; text-align: center; 
                              padding: 20px; letter-spacing: 5px; background-color: #f0f0f0; 
                              border-radius: 8px; margin: 20px 0; }}
                .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 8px; }}
                .footer {{ font-size: 12px; color: #777; text-align: center; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Civic Issues Tracker</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>{full_name}</strong>,</p>
                    <p>Your verification code is:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code expires in <strong>10 minutes</strong>.</p>
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
Hello {full_name},

Your verification code is: {otp_code}

This code expires in 10 minutes.

If you didn't request this, please ignore this email.

Thank you,
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
            print(f"✅ Email OTP sent to {email}")
            return True, "Email sent"
        except Exception as e:
            print(f"❌ Email failed: {e}")
            return False, str(e)
    
    @staticmethod
    def store_pending_user(registration_data, method):
        """Store pending user registration data in Redis cache"""
        temp_id = str(uuid.uuid4())
        otp_code = OTPService.generate_otp()
        
        pending_data = {
            'registration_data': registration_data,
            'otp_code': otp_code,
            'method': method,
            'attempts': 0,
            'resend_count': 0,
            'created_at': timezone.now().isoformat(),
            'temp_id': temp_id
        }
        
        cache_key = f"pending_user_{temp_id}"
        cache.set(cache_key, pending_data, timeout=1200)  # 20 minutes
        
        # Also store by contact to prevent multiple pending registrations
        contact = registration_data.get('email', registration_data.get('phone'))
        if contact:
            contact_key = f"pending_contact_{contact}"
            cache.set(contact_key, temp_id, timeout=1200)
        
        return temp_id, otp_code
    
    @staticmethod
    def get_pending_user(temp_id):
        """Retrieve pending user data from Redis cache"""
        cache_key = f"pending_user_{temp_id}"
        return cache.get(cache_key)
    
    @staticmethod
    def delete_pending_user(temp_id):
        """Delete pending user data from Redis cache"""
        pending_data = OTPService.get_pending_user(temp_id)
        
        if pending_data:
            # Also delete the contact lookup key
            registration_data = pending_data.get('registration_data', {})
            contact = registration_data.get('email', registration_data.get('phone'))
            if contact:
                contact_key = f"pending_contact_{contact}"
                cache.delete(contact_key)
        
        cache_key = f"pending_user_{temp_id}"
        cache.delete(cache_key)
    
    @staticmethod
    def check_existing_pending(contact):
        """Check if there's already a pending registration for this contact"""
        if not contact:
            return False, None, None
        
        contact_key = f"pending_contact_{contact}"
        existing_temp_id = cache.get(contact_key)
        
        if existing_temp_id:
            pending_data = OTPService.get_pending_user(existing_temp_id)
            if pending_data:
                return True, existing_temp_id, pending_data
        
        return False, None, None
    
    @staticmethod
    def verify_otp_and_create_user(temp_id, otp_code):
        """
        Verify OTP and create actual user if valid
        Returns: (success, message, user_object)
        """
        from .models import User, Role, Resident
        from .utils import generate_user_number
        
        pending_data = OTPService.get_pending_user(temp_id)
        
        if not pending_data:
            return False, "Verification session expired. Please register again.", None
        
        # Check attempts
        if pending_data['attempts'] >= 3:
            OTPService.delete_pending_user(temp_id)
            return False, "Too many failed attempts. Please register again.", None
        
        # Verify OTP
        if pending_data['otp_code'] != otp_code:
            # Increment attempts
            pending_data['attempts'] += 1
            cache_key = f"pending_user_{temp_id}"
            cache.set(cache_key, pending_data, timeout=1200)
            remaining = 3 - pending_data['attempts']
            return False, f"Invalid OTP. {remaining} attempts remaining.", None
        
        # OTP verified - create actual user
        registration_data = pending_data['registration_data']
        
        try:
            role = Role.objects.get(name='resident')
            user_number = generate_user_number()
            
            # Create user
            user = User.objects.create_user(
                email=registration_data.get('email', None),
                phone=registration_data.get('phone'),
                password=registration_data['password'],
                full_name=registration_data['full_name'],
                role=role,
                user_number=user_number,
                is_verified=True,
                is_active=True,
                email_verified=(pending_data['method'] == 'email'),
                sms_verified=(pending_data['method'] == 'sms')
            )
            
            # Create resident profile
            Resident.objects.create(user=user)
            
            # Clean up pending data
            OTPService.delete_pending_user(temp_id)
            
            return True, "Account verified and created successfully!", user
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return False, f"Error creating account: {str(e)}", None