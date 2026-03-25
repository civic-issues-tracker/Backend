import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def send_test_email():
    print("=" * 50)
    print("Testing Email Configuration")
    print("=" * 50)
    print(f"From: {settings.DEFAULT_FROM_EMAIL}")
    print(f"From Email Account: {settings.EMAIL_HOST_USER}")
    print("=" * 50)
    
    # Test sending to yeabsiraamaree@gmail.com
    recipient = "yeabsiraamaree@gmail.com"
    
    print(f"\n📧 Sending test email to: {recipient}")
    print(f"   From account: {settings.EMAIL_HOST_USER}")
    print("-" * 50)
    
    try:
        send_mail(
            subject='Test Email - Civic Issues Tracker',
            message=f"""Hello,

This is a test email from Civic Issues Tracker.

Sender Account: {settings.EMAIL_HOST_USER}
Recipient: {recipient}
Time: {django.utils.timezone.now()}

If you received this, your email configuration is working correctly!

Thank you,
Civic Issues Tracker Team""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        print("\n✅ Test email sent successfully!")
        print(f"   From: {settings.EMAIL_HOST_USER}")
        print(f"   To: {recipient}")
        print("\n   Check the inbox of yeabsiraamaree@gmail.com")
        print("   (Also check spam folder if not in inbox)")
        
    except Exception as e:
        print(f"\n❌ Email test failed!")
        print(f"   Error: {e}")
        print("\nPossible issues:")
        print("1. Check your Gmail App Password in .env")
        print("2. Make sure 2-Step Verification is enabled")
        print("3. Check your internet connection")
        return False
    
    return True

if __name__ == '__main__':
    send_test_email()