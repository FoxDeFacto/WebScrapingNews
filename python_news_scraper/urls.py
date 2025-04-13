# python_news_scraper/urls.py (update with frontend routes)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from core import views as core_views

# API information for Swagger documentation
api_info = openapi.Info(
    title="News Scraper API",
    default_version='v1',
    description="API for accessing scraped news articles from multiple sources",
    terms_of_service="https://www.google.com/policies/terms/",
    contact=openapi.Contact(email="contact@newscraper.example"),
    license=openapi.License(name="BSD License"),
)

# Create Swagger schema view
schema_view = get_schema_view(
    api_info,
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Frontend routes
    path('', core_views.home, name='home'),
    path('article/<int:article_id>/', core_views.article_detail, name='article_detail'),
    
    # Admin site
    path('admin/', admin.site.urls),
    
    # API URLs
    path('api/', include('api.urls')),
    
    # Swagger URLs
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)