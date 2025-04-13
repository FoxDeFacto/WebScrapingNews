"""
Scraper for Novinky.cz news site.
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.utils import timezone
import dateutil.parser

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class NovinkyScraper(BaseScraper):
    """
    Scraper for Novinky.cz news website.
    """
    
    def get_article_listings(self) -> List[Dict[str, Any]]:
        """
        Get a list of article data from the main page of Novinky.cz.
        
        Returns:
            List of dictionaries with article data (title, url, etc.)
        """
        articles = []
        try:
            # Get the main page
            soup = self.get_soup(self.base_url)
            
            # Find all articles
            article_elements = soup.select('article.q_h7')
            
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
        # Find the article link
        link_elem = article_elem.select_one('h3 a')
        if not link_elem:
            return None
        
        url = link_elem.get('href', '')
        title = link_elem.get_text(strip=True)
        
        # Extract the category from the URL
        category = self._extract_category_from_url(url)
        
        # Get the summary
        summary_elem = article_elem.select_one('div.g_iT') or article_elem.select_one('p.q_il')
        summary = summary_elem.get_text(strip=True) if summary_elem else ""
        
        # Clean up the summary (remove the date part if present)
        if summary and '·' in summary:
            summary = summary.split('·', 1)[1].strip()
        
        # Get the publication time
        time_elem = article_elem.select_one('time')
        published_at = None
        if time_elem:
            try:
                datetime_str = time_elem.get('datetime')
                if datetime_str:
                    published_at = dateutil.parser.parse(datetime_str)
                else:
                    # Try to parse from the text
                    time_text = time_elem.get_text(strip=True)
                    published_at = self._parse_time_text(time_text)
            except Exception as e:
                logger.warning(f"Error parsing date: {str(e)}")
        
        # Get the image URL
        image_elem = article_elem.select_one('img')
        image_url = ""
        if image_elem:
            # Try different attributes where the image URL might be
            for attr in ['src', 'data-srcset', 'srcset']:
                if attr in image_elem.attrs:
                    attr_value = image_elem[attr]
                    if attr in ['data-srcset', 'srcset']:
                        # Extract the URL from srcset format
                        try:
                            image_url = attr_value.split(' ')[0]
                        except (IndexError, AttributeError):
                            continue
                    else:
                        image_url = attr_value
                    break
        
        return {
            'title': title,
            'url': url,
            'summary': summary,
            'published_at': published_at,
            'image_url': image_url,
            'categories': [category] if category else []
        }
    
    def _extract_category_from_url(self, url: str) -> Optional[str]:
        """
        Extract the category from a Novinky.cz article URL.
        
        Args:
            url: Article URL
            
        Returns:
            Category name or None if not found
        """
        # URL format is typically: https://www.novinky.cz/clanek/kategorie-nazev-clanku-12345678
        try:
            # Extract path and split by slashes
            match = re.search(r'\/clanek\/([^\/]+)', url)
            if match:
                category_slug = match.group(1)
                # The category is typically the first part of the slug
                category = category_slug.split('-', 1)[0]
                
                # Map to properly capitalized category name
                category_map = {
                    'stalo': 'Stalo se',
                    'domaci': 'Domácí',
                    'volby': 'Volby',
                    'zahranicni': 'Zahraniční',
                    'valka': 'Válka na Ukrajině',
                    'krimi': 'Krimi',
                    'ekonomika': 'Ekonomika',
                }
                
                return category_map.get(category, category.capitalize())
        except Exception as e:
            logger.warning(f"Error extracting category from URL {url}: {str(e)}")
        
        return None
    
    def _parse_time_text(self, time_text: str) -> Optional[datetime]:
        """
        Parse time text into a datetime object.
        
        Args:
            time_text: Text containing the publication time
            
        Returns:
            Datetime object or None if parsing failed
        """
        now = timezone.now()
        try:
            # Format examples: "9:32", "Dnes 9:53"
            time_text = time_text.lower()
            
            # Remove "dnes" or similar prefix
            if 'dnes' in time_text:
                time_text = time_text.replace('dnes', '').strip()
            
            # Parse the time
            hour, minute = map(int, time_text.split(':'))
            
            # Create a datetime with today's date and the parsed time
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except Exception as e:
            logger.warning(f"Error parsing time text '{time_text}': {str(e)}")
            return None
    
    def scrape_article_content(self, url: str) -> str:
        """
        Scrape the full content of a Novinky.cz article as clean text.
        
        Args:
            url: URL of the article
            
        Returns:
            Article content as clean text
        """
        try:
            soup = self.get_soup(url)
            
            # Find the article content container
            content_elem = soup.select_one('div.e_es.e_eD')
            if not content_elem:
                return ""
            
            paragraphs = []
            
            # Extract text from all paragraph elements with class containing '7'
            # or heading elements
            for elem in content_elem.find_all(['p', 'h2', 'h3']):
                # Check if it's a heading or if any of the element's classes contain '7'
                if (elem.name in ['h2', 'h3']) or (elem.get('class') and any('7' in cls for cls in elem.get('class', []))):
                    # Extract clean text
                    text = elem.get_text(strip=True)
                    if text:
                        paragraphs.append(text)
            
            # Also handle direct text that might be between paragraphs
            for child in content_elem.children:
                if child.name is None and child.strip():  # Direct text node with content
                    paragraphs.append(child.strip())
            
            # Join paragraphs with double newlines
            return '\n\n'.join(paragraphs)
        
        except Exception as e:
            logger.error(f"Error scraping article content for {url}: {str(e)}")
            self.errors.append(f"Error scraping article content for {url}: {str(e)}")
            return ""
        
        except Exception as e:
            logger.error(f"Error scraping article content for {url}: {str(e)}")
            self.errors.append(f"Error scraping article content for {url}: {str(e)}")
            return ""