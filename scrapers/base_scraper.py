"""
Base scraper class for all news scraper implementations.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from core.models import NewsSource, Category, Article, ScrapingLog

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for scrapers.
    
    All scrapers should inherit from this class and implement the required methods.
    """
    
    def __init__(self, news_source: NewsSource):
        """Initialize the scraper with a news source."""
        self.source = news_source
        self.base_url = news_source.base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
        # Create a scraping log
        self.log = ScrapingLog.objects.create(source=self.source)
        self.articles_found = 0
        self.articles_added = 0
        self.articles_updated = 0
        self.errors = []
    
    def scrape(self) -> None:
        """
        Main scraping method. Orchestrates the scraping process.
        """
        try:
            # Get article URLs from main page
            logger.info(f"Starting scraping for {self.source.name}")
            article_data = self.get_article_listings()
            self.articles_found = len(article_data)
            logger.info(f"Found {self.articles_found} articles on {self.source.name}")
            
            # Process each article
            for data in article_data:
                try:
                    self.process_article(data)
                except Exception as e:
                    error_msg = f"Error processing article {data.get('url', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
            
            # Mark scraping as successful
            self.log.success = True
        except Exception as e:
            error_msg = f"Error during scraping of {self.source.name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            self.log.success = False
        finally:
            # Update the log
            self.log.articles_found = self.articles_found
            self.log.articles_added = self.articles_added
            self.log.articles_updated = self.articles_updated
            self.log.errors = '\n'.join(self.errors)
            self.log.finished_at = timezone.now()
            self.log.save()
    
    def process_article(self, article_data: Dict[str, Any]) -> Optional[Article]:
        """
        Process a single article. Creates or updates an Article instance.
        
        Args:
            article_data: Dictionary with article data (title, url, etc.)
            
        Returns:
            The created or updated Article instance, or None if processing failed.
        """
        url = article_data.get('url')
        if not url:
            logger.warning("Article data missing URL, skipping")
            return None
        
        # Make sure URL is absolute
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        
        # Check if article already exists
        try:
            article = Article.objects.get(url=url)
            created = False
        except Article.DoesNotExist:
            article = Article(url=url, source=self.source)
            created = True
        
        # Update article data
        article.title = article_data.get('title', '')
        article.summary = article_data.get('summary', '')
        
        # If we have a publication date, use it
        published_at = article_data.get('published_at')
        if published_at:
            article.published_at = published_at
        elif created:  # Only set for new articles
            article.published_at = timezone.now()
        
        # Save image URL if present
        if 'image_url' in article_data:
            article.image_url = article_data['image_url']
        
        # Save the article
        article.save()
        
        # Add categories if present
        if 'categories' in article_data and article_data['categories']:
            for category_name in article_data['categories']:
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': self.slugify_category(category_name)}
                )
                article.categories.add(category)
        
        # If we have content, update it
        if 'content' in article_data:
            article.content = article_data['content']
            article.save(update_fields=['content'])
        # Otherwise, try to scrape the full article content
        elif created or not article.content:
            try:
                content = self.scrape_article_content(url)
                if content:
                    article.content = content
                    article.save(update_fields=['content'])
            except Exception as e:
                logger.error(f"Error scraping content for {url}: {str(e)}")
                self.errors.append(f"Error scraping content for {url}: {str(e)}")
        
        # Update statistics
        if created:
            self.articles_added += 1
            logger.info(f"Added new article: {article.title}")
        else:
            self.articles_updated += 1
            logger.info(f"Updated existing article: {article.title}")
        
        return article
    
    def get_soup(self, url: str) -> BeautifulSoup:
        """
        Get BeautifulSoup object from URL.
        
        Args:
            url: URL to retrieve
            
        Returns:
            BeautifulSoup object
        
        Raises:
            requests.RequestException: If request fails
        """
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')
    
    """
    Addition to BaseScraper class to handle text cleaning.
    """
    def clean_html_content(self, html_content: str) -> str:
        """
        Clean HTML content to provide plain text while preserving structure.
        
        Args:
            html_content: HTML content string
            
        Returns:
            Clean text with preserved paragraph structure
        """
        if not html_content:
            return ""
        
        # Create a BeautifulSoup object to parse the HTML
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Replace <br> tags with newline characters
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        # Process paragraphs
        paragraphs = []
        for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Get the text content of the paragraph
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)
        
        # Join paragraphs with double newlines to preserve structure
        clean_text = '\n\n'.join(paragraphs)
        
        # Remove any extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Replace multiple newlines with double newlines
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        
        return clean_text
    
    def slugify_category(self, category_name: str) -> str:
        """
        Convert a category name to a slug.
        
        Args:
            category_name: Category name
            
        Returns:
            Category slug
        """
        # Simple slugify implementation
        slug = category_name.lower().replace(' ', '-')
        return ''.join(c for c in slug if c.isalnum() or c == '-')
    
    @abstractmethod
    def get_article_listings(self) -> List[Dict[str, Any]]:
        """
        Get a list of article data from the main page.
        
        Returns:
            List of dictionaries with article data (title, url, etc.)
        """
        pass
    
    @abstractmethod
    def scrape_article_content(self, url: str) -> str:
        """
        Scrape the full content of an article.
        
        Args:
            url: URL of the article
            
        Returns:
            Article content as HTML
        """
        pass