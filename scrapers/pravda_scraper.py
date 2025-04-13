"""
Scraper for Pravda.com.ua news site.
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.utils import timezone
import dateutil.parser

from core.models import Category  # Added missing import
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PravdaScraper(BaseScraper):
    """
    Scraper for Pravda.com.ua news website.
    """
    
    def get_article_listings(self) -> List[Dict[str, Any]]:
        """
        Get a list of article data from the main page of Pravda.com.ua.
        
        Returns:
            List of dictionaries with article data (title, url, etc.)
        """
        articles = []
        try:
            # Get the main page
            soup = self.get_soup(self.base_url)
            
            # Find all article containers
            article_elements = soup.select('div[data-vr-contentbox]')
            
            for article_elem in article_elements:
                try:
                    # Extract article data
                    article_data = self._extract_article_data(article_elem)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    logger.error(f"Error extracting article data: {str(e)}")
                    self.errors.append(f"Error extracting article data: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error scraping article listings: {str(e)}")
            self.errors.append(f"Error scraping article listings: {str(e)}")
        
        return articles
    
    def _extract_article_data(self, article_elem: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract data from an article element.
        
        Args:
            article_elem: BeautifulSoup element representing an article
            
        Returns:
            Dictionary with article data, or None if extraction failed
        """
        # Get the title and URL from the data attributes
        title = article_elem.get('data-vr-contentbox', '')
        url_path = article_elem.get('data-vr-contentbox-url', '')
        
        if not url_path:
            # Try to find the link inside the article element
            link_elem = article_elem.select_one('a[href]')
            if link_elem:
                url_path = link_elem.get('href', '')
                if not title:
                    title = link_elem.get_text(strip=True)
        
        if not url_path or not title:
            return None
        
        # Make the URL absolute
        url = urljoin(self.base_url, url_path)
        
        # Get the image URL - try both source and img elements
        image_url = ""
        image_elem = article_elem.select_one('picture img')
        if image_elem and 'src' in image_elem.attrs:
            image_url = image_elem['src']
        else:
            # Try to find source element with srcset
            source_elem = article_elem.select_one('picture source')
            if source_elem and 'srcset' in source_elem.attrs:
                image_url = source_elem['srcset']
                
        # Make the image URL absolute if needed
        if image_url and not image_url.startswith(('http://', 'https://')):
            image_url = urljoin(self.base_url, image_url)
        
        # We don't have categories or published_at from the main page
        # We'll try to extract these from the article page later
        
        return {
            'title': title,
            'url': url,
            'summary': "",  # Will be populated from the article page
            'image_url': image_url,
            'categories': [],  # Will be populated from the article page
            'published_at': None  # Will be populated from the article page
        }
    
    def scrape_article_content(self, url: str) -> str:
        """
        Scrape the full content of a Pravda.com.ua article as clean text.
        
        Args:
            url: URL of the article
            
        Returns:
            Article content as clean text
        """
        try:
            soup = self.get_soup(url)
            
            # Find the article content container
            content_elem = soup.select_one('div.post_text')
            if not content_elem:
                return ""
            
            # Extract article metadata while we're here
            self._extract_article_metadata(url, soup)
            
            # Extract all text from paragraphs
            paragraphs = []
            for elem in content_elem.find_all(['p', 'h2', 'h3', 'h4']):
                text = elem.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            
            # Join paragraphs with double newlines
            return '\n\n'.join(paragraphs)
        
        except Exception as e:
            logger.error(f"Error scraping article content for {url}: {str(e)}")
            self.errors.append(f"Error scraping article content for {url}: {str(e)}")
            return ""
    
    def _extract_article_metadata(self, url: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract metadata from an article page.
        
        Args:
            url: URL of the article
            soup: BeautifulSoup object of the article page
            
        Returns:
            Dictionary with metadata (published_at, summary, categories)
        """
        metadata = {
            'published_at': None,
            'summary': "",
            'categories': []
        }
        
        try:
            # Extract publication date and time
            time_elem = soup.select_one('div.post_time')
            if time_elem:
                date_text = time_elem.get_text(strip=True)
                try:
                    # Example format: "Неділя, 13 квітня 2025, 10:59"
                    date_match = re.search(r'(\d+)\s+(\w+)\s+(\d{4}),\s+(\d+):(\d+)', date_text)
                    if date_match:
                        day, month_name, year, hour, minute = date_match.groups()
                        
                        # Map Ukrainian month names to numbers
                        month_map = {
                            'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
                            'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
                            'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
                        }
                        
                        month = month_map.get(month_name.lower(), 1)
                        metadata['published_at'] = datetime(
                            int(year), month, int(day), int(hour), int(minute)
                        )
                except Exception as e:
                    logger.warning(f"Error parsing date '{date_text}': {str(e)}")
            
            # Extract summary - usually the first paragraph with actual content
            first_p = None
            for p in soup.select('div.post_text p'):
                text = p.get_text(strip=True)
                if text and len(text) > 30:  # Minimal meaningful summary
                    first_p = p
                    break
                    
            if first_p:
                metadata['summary'] = first_p.get_text(strip=True)
            
            # Extract categories from post_tags class
            tags_container = soup.select_one('div.post_tags')
            if tags_container:
                for tag_elem in tags_container.select('a'):
                    tag_text = tag_elem.get_text(strip=True)
                    if tag_text:
                        metadata['categories'].append(tag_text)
            
            # Update the corresponding Article instance with this metadata if it exists
            try:
                article = self.source.articles.get(url=url)
                
                if metadata['published_at']:
                    article.published_at = metadata['published_at']
                
                if metadata['summary']:
                    article.summary = metadata['summary']
                
                article.save()
                
                # Add categories
                for category_name in metadata['categories']:
                    category, _ = Category.objects.get_or_create(
                        name=category_name,
                        defaults={'slug': self.slugify_category(category_name)}
                    )
                    article.categories.add(category)
                    
            except Exception as e:
                logger.error(f"Error updating article with metadata for {url}: {str(e)}")
                self.errors.append(f"Error updating article with metadata for {url}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error extracting metadata for {url}: {str(e)}")
            self.errors.append(f"Error extracting metadata for {url}: {str(e)}")
        
        return metadata