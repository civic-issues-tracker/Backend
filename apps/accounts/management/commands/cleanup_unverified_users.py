from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Clean up any unverified users that might have been created (fallback)'
    
    def handle(self, *args, **options):
        # This is just a fallback - with the new OTP flow, users aren't created until verified
        # But in case any were created incorrectly, this cleans them up
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        unverified_users = User.objects.filter(
            is_verified=False,
            created_at__lt=cutoff_time
        )
        
        count = unverified_users.count()
        unverified_users.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count} unverified users')
        )