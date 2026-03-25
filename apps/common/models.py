from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    """
    Custom manager that returns only active (non-deleted) objects by default
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def all_with_inactive(self):
        """Return all objects including inactive ones"""
        return super().get_queryset()
    
    def inactive_only(self):
        """Return only inactive (deleted) objects"""
        return super().get_queryset().filter(is_active=False)


class BaseModel(models.Model):
    """
    Abstract base model with soft delete capability.
    All models that need soft delete should inherit from this.
    """
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft delete flag. False means the record is deleted/inactive"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the record was soft deleted"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom managers
    objects = ActiveManager()
    all_objects = models.Manager()  # Includes all objects (active and inactive)
    
    def soft_delete(self):
        """
        Soft delete - mark as inactive instead of removing from database
        """
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at', 'updated_at'])
    
    def activate(self):
        """
        Restore/activate a soft-deleted object
        """
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=['is_active', 'deleted_at', 'updated_at'])
    
    class Meta:
        abstract = True