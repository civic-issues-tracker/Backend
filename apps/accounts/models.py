import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        """
        Create a regular user.
        Email is optional - can be empty for users who only use phone.
        """
        if email:
            email = self.normalize_email(email)
        else:
            email = None  # Empty string for users without email
        
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create a superuser. Email is required for superusers.
        """
        if not email:
            raise ValueError('Superuser must have an email')
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        role, _ = Role.objects.get_or_create(
            name='system_admin',
            defaults={'description': 'System Administrator'}
        )
        extra_fields['role'] = role
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True, default=None)
    phone = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    organization = models.ForeignKey('organizations.Organization', 
                                     on_delete=models.SET_NULL, 
                                     null=True, blank=True)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    telegram_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    last_login = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    telegram_chat_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    telegram_username = models.CharField(max_length=100, null=True, blank=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email or self.phone})"


class Resident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resident_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'residents'

    def __str__(self):
        return f"Resident: {self.user.full_name}"


class OrganizationAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='org_admin_profile')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organization_admins'

    def __str__(self):
        return f"Org Admin: {self.user.full_name}"


class SystemAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='system_admin_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_admins'

    def __str__(self):
        return f"System Admin: {self.user.full_name}"