"""
Models for the news scraper application.
"""
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class NewsSource(models.Model):
    """
    A news source (website) from which articles are scraped.
    """
    name = models.CharField(_("Name"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=100, unique=True)
    base_url = models.URLField(_("Base URL"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    language = models.CharField(_("Language"), max_length=10, 
                               help_text=_("ISO 639-1 language code (e.g., 'cs', 'uk')"))
    active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("News Source")
        verbose_name_plural = _("News Sources")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    """
    A category for news articles.
    """
    name = models.CharField(_("Name"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)
    
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Article(models.Model):
    """
    A news article scraped from a source.
    """
    title = models.CharField(_("Title"), max_length=500)
    source = models.ForeignKey(
        NewsSource, 
        on_delete=models.CASCADE, 
        related_name="articles",
        verbose_name=_("Source")
    )
    url = models.URLField(_("URL"), max_length=500, unique=True)
    summary = models.TextField(_("Summary"), blank=True)
    content = models.TextField(_("Content"), blank=True)
    image_url = models.URLField(_("Image URL"), max_length=500, blank=True)
    published_at = models.DateTimeField(_("Published at"), null=True, blank=True)
    categories = models.ManyToManyField(
        Category, 
        related_name="articles",
        verbose_name=_("Categories"),
        blank=True
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['source', '-published_at']),
        ]

    def __str__(self):
        return self.title


class ScrapingLog(models.Model):
    """
    Log for scraping operations.
    """
    source = models.ForeignKey(
        NewsSource, 
        on_delete=models.CASCADE, 
        related_name="scraping_logs",
        verbose_name=_("Source")
    )
    started_at = models.DateTimeField(_("Started at"), auto_now_add=True)
    finished_at = models.DateTimeField(_("Finished at"), null=True, blank=True)
    articles_found = models.IntegerField(_("Articles found"), default=0)
    articles_added = models.IntegerField(_("Articles added"), default=0)
    articles_updated = models.IntegerField(_("Articles updated"), default=0)
    errors = models.TextField(_("Errors"), blank=True)
    success = models.BooleanField(_("Success"), default=False)

    class Meta:
        verbose_name = _("Scraping Log")
        verbose_name_plural = _("Scraping Logs")
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.source.name} - {self.started_at}"