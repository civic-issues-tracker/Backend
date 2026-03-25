import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from apps.accounts.models import User, Role


def ensure_superuser():
    email = settings.SUPERUSER_EMAIL
    password = settings.SUPERUSER_PASSWORD
    
    if not User.objects.filter(email=email).exists():
        role, _ = Role.objects.get_or_create(
            name='system_admin',
            defaults={'description': 'System Administrator'}
        )
        
        User.objects.create_superuser(
            email=email,
            password=password,
            full_name=settings.SUPERUSER_NAME,
            phone=settings.SUPERUSER_PHONE,
            role=role
        )
        print(f"✅ Superuser created: {email}")
    else:
        print(f"⏩ Superuser already exists: {email}")


if __name__ == '__main__':
    ensure_superuser()