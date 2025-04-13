"""
Serializers for the API.
"""
from rest_framework import serializers
from core.models import NewsSource, Category, Article


class NewsSourceSerializer(serializers.ModelSerializer):
    """Serializer for NewsSource model."""
    
    class Meta:
        model = NewsSource
        fields = ('id', 'name', 'slug', 'base_url', 'description', 'language', 'active')


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description')


class ArticleListSerializer(serializers.ModelSerializer):
    """Serializer for Article model (list view)."""
    source = serializers.StringRelatedField()
    categories = serializers.StringRelatedField(many=True)
    source_slug = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = ('id', 'title', 'source', 'source_slug', 'url', 'summary', 
                 'image_url', 'published_at', 'categories')
    
    def get_source_slug(self, obj):
        """Get the slug of the source."""
        return obj.source.slug


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Serializer for Article model (detail view)."""
    source = NewsSourceSerializer()
    categories = CategorySerializer(many=True)
    
    class Meta:
        model = Article
        fields = ('id', 'title', 'source', 'url', 'summary', 'content', 
                 'image_url', 'published_at', 'categories', 'created_at', 'updated_at')