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
            logger.info(f"Fetching content from URL: {self.base_url}")
            soup = self.get_soup(self.base_url)
            
            # Log the structure for debugging
            logger.info(f"Page title: {soup.title.string if soup.title else 'No title found'}")
            
            # Try multiple selectors to find articles
            selectors = [
                'article.q_h7',               # Original selector
                'article',                     # Generic article tag
                'div.article, div.list-art',   # Alternative article containers
                '.article-tile',               # Another common pattern
            ]
            
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                article_elements = soup.select(selector)
                logger.info(f"Found {len(article_elements)} elements with selector '{selector}'")
                
                if article_elements:
                    break  # Found articles, no need to try other selectors
            
            # If no articles found with any selector, try a more detailed page analysis
            if not article_elements:
                logger.warning("No articles found with common selectors. Performing detailed page analysis.")
                
                # Analyze the page structure to help diagnose the issue
                all_tags = {}
                for tag in soup.find_all():
                    tag_name = tag.name
                    if tag_name in all_tags:
                        all_tags[tag_name] += 1
                    else:
                        all_tags[tag_name] = 1
                
                logger.info(f"Page contains the following tags: {all_tags}")
                
                # Look specifically for links that might be articles
                potential_articles = []
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag.get('href', '')
                    # Check if it looks like an article link
                    if '/clanek/' in href:
                        potential_articles.append(a_tag.parent)
                
                logger.info(f"Found {len(potential_articles)} potential article links")
                article_elements = potential_articles
            
            # Process found articles
            for article_elem in article_elements:
                try:
                    # Extract article data
                    logger.info(f"Processing article element: {article_elem.name}.{'.'.join(article_elem.get('class', []))}")
                    article_data = self._extract_article_data(article_elem)
                    if article_data:
                        articles.append(article_data)
                        logger.info(f"Successfully extracted article: {article_data['title']}")
                    else:
                        logger.warning(f"Failed to extract data from article element")
                except Exception as e:
                    logger.error(f"Error extracting article data: {str(e)}")
                    self.errors.append(f"Error extracting article data: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error scraping article listings: {str(e)}")
            self.errors.append(f"Error scraping article listings: {str(e)}")
        
        logger.info(f"Total articles found: {len(articles)}")
        return articles
    
    def _extract_article_data(self, article_elem: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract data from an article element.
        
        Args:
            article_elem: BeautifulSoup element representing an article
            
        Returns:
            Dictionary with article data, or None if extraction failed
        """
        # Try multiple selectors for the link
        link_elem = None
        for selector in ['h3 a', 'h2 a', 'h4 a', 'a.title', '.title a', 'a[href*="/clanek/"]', 'a']:
            logger.debug(f"Trying to find link with selector: {selector}")
            link_elem = article_elem.select_one(selector)
            if link_elem:
                logger.debug(f"Found link with selector: {selector}")
                break
        
        if not link_elem:
            logger.warning("No link element found in article")
            return None
        
        url = link_elem.get('href', '')
        if not url:
            logger.warning("Link has no href attribute")
            return None
            
        # Make sure URL is absolute
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        
        title = link_elem.get_text(strip=True)
        if not title:
            logger.warning(f"No title found for URL: {url}")
            return None
            
        logger.info(f"Found article: '{title}' at URL: {url}")
        
        # Extract the category from the URL
        category = self._extract_category_from_url(url)
        logger.debug(f"Extracted category: {category}")
        
        # Get the summary - try multiple selectors
        summary = ""
        for selector in ['div.g_iT', 'p.q_il', 'div.perex', 'p.perex', '.article-perex', '.summary']:
            summary_elem = article_elem.select_one(selector)
            if summary_elem:
                summary = summary_elem.get_text(strip=True)
                logger.debug(f"Found summary with selector: {selector}")
                break
        
        # Clean up the summary (remove the date part if present)
        if summary and '·' in summary:
            summary = summary.split('·', 1)[1].strip()
        
        # Get the publication time - try multiple selectors
        published_at = None
        for selector in ['time', '.time', '.date', 'span.date', '[datetime]']:
            time_elem = article_elem.select_one(selector)
            if time_elem:
                try:
                    # First try to get the datetime attribute
                    datetime_str = time_elem.get('datetime')
                    if datetime_str:
                        published_at = dateutil.parser.parse(datetime_str)
                        logger.debug(f"Parsed datetime attribute: {published_at}")
                        break
                    else:
                        # Try to parse from the text
                        time_text = time_elem.get_text(strip=True)
                        published_at = self._parse_time_text(time_text)
                        if published_at:
                            logger.debug(f"Parsed time from text: {published_at}")
                            break
                except Exception as e:
                    logger.warning(f"Error parsing date: {str(e)}")
        
        # Get the image URL - try multiple approaches
        image_url = ""
        
        # Try direct img tag
        for selector in ['img', 'picture img', '.thumbnail img', '.image img']:
            image_elem = article_elem.select_one(selector)
            if image_elem:
                # Try different attributes where the image URL might be
                for attr in ['src', 'data-src', 'data-srcset', 'srcset']:
                    if attr in image_elem.attrs:
                        attr_value = image_elem.get(attr, '')
                        if attr in ['data-srcset', 'srcset']:
                            # Extract the URL from srcset format
                            try:
                                image_url = attr_value.split(' ')[0]
                            except (IndexError, AttributeError):
                                continue
                        else:
                            image_url = attr_value
                        
                        if image_url:
                            logger.debug(f"Found image URL: {image_url}")
                            break
                
                if image_url:
                    break
        
        # If no image URL found, try background image in style attribute
        if not image_url:
            for element in article_elem.select('[style*="background"]'):
                style = element.get('style', '')
                match = re.search(r'background(?:-image)?\s*:\s*url\([\'"]?([^\'"]+)[\'"]?\)', style)
                if match:
                    image_url = match.group(1)
                    logger.debug(f"Found background image URL: {image_url}")
                    break
        
        # Make sure image URL is absolute
        if image_url and not image_url.startswith(('http://', 'https://')):
            image_url = urljoin(self.base_url, image_url)
        
        article_data = {
            'title': title,
            'url': url,
            'summary': summary,
            'published_at': published_at,
            'image_url': image_url,
            'categories': [category] if category else []
        }
        
        logger.info(f"Extracted article data: {article_data['title']} - URL: {article_data['url']}")
        return article_data
    
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
        logger.debug(f"Attempting to parse time text: '{time_text}'")
        
        try:
            # Format examples: "9:32", "Dnes 9:53"
            time_text = time_text.lower()
            
            # Remove "dnes" or similar prefix
            if 'dnes' in time_text:
                time_text = time_text.replace('dnes', '').strip()
            
            # Handle other Czech date formats
            if 'včera' in time_text:
                # Yesterday
                time_text = time_text.replace('včera', '').strip()
                base_date = now.date() - timezone.timedelta(days=1)
            elif any(day in time_text for day in ['po', 'út', 'st', 'čt', 'pá', 'so', 'ne']):
                # Day of week abbreviation - use today
                time_text = re.sub(r'(po|út|st|čt|pá|so|ne)\s+', '', time_text).strip()
                base_date = now.date()
            else:
                # Default to today
                base_date = now.date()
            
            # Parse the time
            if ':' in time_text:
                time_parts = time_text.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1].split()[0])  # Handle additional text after minutes
                
                # Create a datetime with the determined date and the parsed time
                return datetime.combine(base_date, datetime.time(hour, minute, 0))
            else:
                logger.warning(f"Time text doesn't contain ':' separator: {time_text}")
                return None
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
            logger.info(f"Scraping article content from URL: {url}")
            soup = self.get_soup(url)
            
            # Log the article page title for debugging
            logger.info(f"Article page title: {soup.title.string if soup.title else 'No title found'}")
            
            # Try multiple selectors for the article content container
            content_elem = None
            for selector in ['div.e_es.e_eD', 'div.article-content', '.article-body', 'article', '.article-detail-content']:
                logger.debug(f"Trying to find content with selector: {selector}")
                content_elem = soup.select_one(selector)
                if content_elem:
                    logger.debug(f"Found content container with selector: {selector}")
                    break
            
            if not content_elem:
                logger.warning("No content container found in article page")
                return ""
            
            paragraphs = []
            
            # Extract text from different types of elements
            for elem_type in ['p', 'h2', 'h3', 'div.paragraph', '.article-text']:
                logger.debug(f"Looking for content in elements: {elem_type}")
                elements = content_elem.select(elem_type)
                logger.debug(f"Found {len(elements)} {elem_type} elements")
                
                for elem in elements:
                    # Skip elements that are likely not part of the main content
                    skip_classes = ['date', 'author', 'meta', 'social', 'related', 'share', 'comments']
                    if any(cls in str(elem.get('class', '')) for cls in skip_classes):
                        continue
                    
                    text = elem.get_text(strip=True)
                    if text and len(text) > 5:  # Skip very short texts
                        paragraphs.append(text)
                        logger.debug(f"Added paragraph: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # If no paragraphs found with specific selectors, try a more general approach
            if not paragraphs:
                logger.warning("No paragraphs found with specific selectors. Trying generic approach.")
                
                # Look for text content in any div with class containing '7' (as per original logic)
                for elem in content_elem.find_all(['p', 'h2', 'h3', 'div']):
                    # Check class attribute
                    if elem.get('class') and any('7' in cls for cls in elem.get('class', [])):
                        text = elem.get_text(strip=True)
                        if text:
                            paragraphs.append(text)
                            logger.debug(f"Added paragraph from class '7': {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Also handle direct text that might be between paragraphs
            for child in content_elem.children:
                if child.name is None and child.strip():  # Direct text node with content
                    text = child.strip()
                    if len(text) > 30:  # Only add substantial text
                        paragraphs.append(text)
                        logger.debug(f"Added direct text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Join paragraphs with double newlines
            content = '\n\n'.join(paragraphs)
            if content:
                logger.info(f"Successfully extracted article content: {len(content)} characters, {len(paragraphs)} paragraphs")
            else:
                logger.warning("No content extracted from article")
            
            return content
        
        except Exception as e:
            logger.error(f"Error scraping article content for {url}: {str(e)}")
            self.errors.append(f"Error scraping article content for {url}: {str(e)}")
            return ""