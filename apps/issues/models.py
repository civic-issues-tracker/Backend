import uuid
from django.db import models
from apps.common.models import BaseModel


class Issue(BaseModel):
    """
    TEMPORARY PLACEHOLDER - Will be replaced with full Issue model later
    This exists only to make relationships work while building other apps.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Relationships (placeholders)
    category = models.ForeignKey(
        'organizations.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issues'
    )
    subcategory = models.ForeignKey(
        'organizations.SubCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issues'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issues'
    )
    
    class Meta:
        db_table = 'issues'
        verbose_name = 'Issue (Placeholder)'
        verbose_name_plural = 'Issues (Placeholder)'

    def __str__(self):
        return f"Issue {self.issue_number or self.id}"