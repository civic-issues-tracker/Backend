import uuid
from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel


class Organization(BaseModel):
    """
    Department/Organization that handles civic issues
    Examples: Water Utility - Bole, Fire Dept - Kirkos, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name}" + (" (Inactive)" if not self.is_active else "")


class Category(BaseModel):
    """
    Main issue category (Water, Fire, Electricity, Road Damage)
    System Admin can create/update/delete categories
    """
    CATEGORY_CHOICES = [
        ('water', 'Water'),
        ('fire', 'Fire'),
        ('electricity', 'Electricity'),
        ('road_damage', 'Road Damage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    # Many-to-Many relationship with Organization through CategoryOrganization
    organizations = models.ManyToManyField(
        Organization,
        through='CategoryOrganization',
        related_name='categories',
        through_fields=('category', 'organization')
    )

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.get_name_display() + (" (Inactive)" if not self.is_active else "")


class CategoryOrganization(BaseModel):
    """
    Junction table linking categories to organizations (Many-to-Many)
    Allows:
        - One category to be handled by multiple organizations
        - One organization to handle multiple categories
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='category_organizations'
    )
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='category_organizations'
    )

    class Meta:
        db_table = 'category_organizations'
        unique_together = ['category', 'organization']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['category', 'organization']),
        ]

    def __str__(self):
        return f"{self.category.get_name_display()} → {self.organization.name}"


class SubCategory(BaseModel):
    """
    Specific issue subcategory under a main category
    Examples: Under Water → Leakage, Shortage, Pollution
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='subcategories'
    )
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'sub_categories'
        unique_together = ['category', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['category', 'is_active']),
        ]

    def clean(self):
        """Validate that subcategory name is unique within its category"""
        if SubCategory.objects.filter(
            category=self.category, 
            name__iexact=self.name
        ).exclude(id=self.id).exists():
            raise ValidationError(
                f"Subcategory '{self.name}' already exists under this category"
            )

    def __str__(self):
        return f"{self.category.get_name_display()} - {self.name}" + (" (Inactive)" if not self.is_active else "")