"""
API views for the news scraper application.
"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from core.models import NewsSource, Category, Article
from .serializers import (
    NewsSourceSerializer, CategorySerializer, 
    ArticleListSerializer, ArticleDetailSerializer
)
from .filters import ArticleFilter


class NewsSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for news sources.
    
    list:
    Return a list of all news sources.
    
    retrieve:
    Return the given news source.
    
    articles:
    Return all articles from the given news source.
    """
    queryset = NewsSource.objects.filter(active=True)
    serializer_class = NewsSourceSerializer
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def articles(self, request, slug=None):
        """Return all articles from a specific source."""
        source = self.get_object()
        articles = Article.objects.filter(source=source)
        
        # Apply filters
        filter_backend = ArticleFilter(request.query_params, queryset=articles)
        articles = filter_backend.qs
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for categories.
    
    list:
    Return a list of all categories.
    
    retrieve:
    Return the given category.
    
    articles:
    Return all articles in the given category.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def articles(self, request, slug=None):
        """Return all articles in a specific category."""
        category = self.get_object()
        articles = Article.objects.filter(categories=category)
        
        # Apply filters
        filter_backend = ArticleFilter(request.query_params, queryset=articles)
        articles = filter_backend.qs
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for articles.
    
    list:
    Return a list of all articles.
    
    retrieve:
    Return the given article.
    """
    queryset = Article.objects.all()
    filterset_class = ArticleFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'summary', 'content']
    ordering_fields = ['published_at', 'created_at']
    ordering = ['-published_at']
    
    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request."""
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleListSerializer