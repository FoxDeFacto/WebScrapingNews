"""
Filters for the API.
"""
import django_filters
from core.models import Article


class ArticleFilter(django_filters.FilterSet):
    """Filter for Article model."""
    title = django_filters.CharFilter(lookup_expr='icontains')
    summary = django_filters.CharFilter(lookup_expr='icontains')
    content = django_filters.CharFilter(lookup_expr='icontains')
    source = django_filters.CharFilter(field_name='source__slug')
    category = django_filters.CharFilter(field_name='categories__slug')
    published_after = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='gte')
    published_before = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='lte')
    
    class Meta:
        model = Article
        fields = [
            'title', 'summary', 'content', 
            'source', 'category', 
            'published_after', 'published_before'
        ]