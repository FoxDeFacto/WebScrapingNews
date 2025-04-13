"""
URL configuration for the API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NewsSourceViewSet, CategoryViewSet, ArticleViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'sources', NewsSourceViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'articles', ArticleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]