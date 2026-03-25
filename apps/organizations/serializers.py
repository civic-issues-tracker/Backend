from rest_framework import serializers
from django.db import transaction
from .models import Organization, Category, SubCategory, CategoryOrganization


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'description', 'contact_email', 'contact_phone',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']


class SubCategorySerializer(serializers.ModelSerializer):
    """Serializer for SubCategory model"""
    category_name = serializers.CharField(source='category.get_name_display', read_only=True)

    class Meta:
        model = SubCategory
        fields = [
            'id', 'category', 'category_name', 'name', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def validate(self, data):
        """Ensure subcategory name is unique within the category"""
        category = data.get('category')
        name = data.get('name')
        
        instance_id = self.instance.id if self.instance else None
        if SubCategory.objects.filter(
            category=category, 
            name__iexact=name
        ).exclude(id=instance_id).exists():
            raise serializers.ValidationError(
                {"name": f"Subcategory '{name}' already exists under this category"}
            )
        return data


class CategorySerializer(serializers.ModelSerializer):
    organizations = OrganizationSerializer(many=True, read_only=True)
    organization_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    subcategory_count = serializers.IntegerField(
        source='subcategories.count', 
        read_only=True
    )
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'organizations', 'organization_ids',
            'subcategory_count', 'subcategories', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def validate_name(self, value):
        """Ensure category name is unique (case-insensitive)"""
        instance_id = self.instance.id if self.instance else None
        if Category.objects.filter(name__iexact=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError(f"Category '{value}' already exists.")
        return value.title()  

class CategoryDetailSerializer(CategorySerializer):
    """Detailed Category serializer with additional statistics"""
    organization_count = serializers.IntegerField(source='organizations.count', read_only=True)
    total_issues = serializers.IntegerField(read_only=True)
    active_subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + [
            'organization_count', 'total_issues', 'active_subcategories'
        ]

    def get_active_subcategories(self, obj):
        """Get only active subcategories"""
        return SubCategorySerializer(
            obj.subcategories.filter(is_active=True), 
            many=True
        ).data