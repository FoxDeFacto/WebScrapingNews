"""
Admin configuration for core app models.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import NewsSource, Category, Article, ScrapingLog


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    """Admin configuration for NewsSource model."""
    list_display = ('name', 'base_url', 'language', 'active', 'created_at')
    list_filter = ('active', 'language', 'created_at')
    search_fields = ('name', 'base_url', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'base_url', 'description')
        }),
        ('Settings', {
            'fields': ('language', 'active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model."""
    list_display = ('name', 'slug', 'article_count')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    def article_count(self, obj):
        """Return the number of articles in this category."""
        return obj.articles.count()
    article_count.short_description = 'Article Count'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin configuration for Article model."""
    list_display = ('title', 'source', 'published_at', 'display_categories', 'display_image', 'created_at')
    list_filter = ('source', 'categories', 'published_at', 'created_at')
    search_fields = ('title', 'summary', 'content')
    readonly_fields = ('display_image_large', 'created_at', 'updated_at')
    filter_horizontal = ('categories',)
    date_hierarchy = 'published_at'
    fieldsets = (
        (None, {
            'fields': ('title', 'source', 'url', 'published_at')
        }),
        ('Content', {
            'fields': ('summary', 'content', 'categories')
        }),
        ('Media', {
            'fields': ('image_url', 'display_image_large')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_categories(self, obj):
        """Return a comma-separated list of category names."""
        return ", ".join([category.name for category in obj.categories.all()])
    display_categories.short_description = 'Categories'
    
    def display_image(self, obj):
        """Display a thumbnail of the article image."""
        if obj.image_url:
            return format_html('<img src="{}" width="50" height="30" style="object-fit: cover;" />', obj.image_url)
        return "-"
    display_image.short_description = 'Image'
    
    def display_image_large(self, obj):
        """Display a larger image of the article."""
        if obj.image_url:
            return format_html('<img src="{}" width="400" style="max-height: 300px; object-fit: contain;" />', obj.image_url)
        return "-"
    display_image_large.short_description = 'Image Preview'


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    """Admin configuration for ScrapingLog model."""
    list_display = ('source', 'started_at', 'finished_at', 'articles_found', 
                   'articles_added', 'articles_updated', 'success')
    list_filter = ('source', 'success', 'started_at')
    readonly_fields = ('started_at', 'finished_at', 'articles_found', 
                      'articles_added', 'articles_updated', 'errors', 'success')
    fieldsets = (
        (None, {
            'fields': ('source', 'success')
        }),
        ('Statistics', {
            'fields': ('articles_found', 'articles_added', 'articles_updated')
        }),
        ('Timing', {
            'fields': ('started_at', 'finished_at')
        }),
        ('Errors', {
            'fields': ('errors',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable the ability to add scraping logs through the admin."""
        return False