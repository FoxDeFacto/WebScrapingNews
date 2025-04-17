"""
Scraper for The Guardian news site.
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from django.conf import settings

from bs4 import BeautifulSoup
from django.utils import timezone
import dateutil.parser

from core.models import Category
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GuardianScraper(BaseScraper):
    """
    Scraper for The Guardian news website.
    """
    
    def get_article_listings(self) -> List[Dict[str, Any]]:
        """
        Get a list of article data from The Guardian.
        
        Returns:
            List of dictionaries with article data (title, url, etc.)
        """
        articles = []
        
        sections = ['europe']  # Default fallback
        
        if hasattr(settings, 'SCRAPER_CONFIG') and 'guardian' in settings.SCRAPER_CONFIG:
            config = settings.SCRAPER_CONFIG['guardian']
            if 'sections_of_interest' in config:
                sections = config['sections_of_interest']
        
        try:
            # First scrape the main URL (Europe section by default)
            logger.info(f"Fetching content from main URL: {self.base_url}")
            main_articles = self._scrape_section(self.base_url)
            articles.extend(main_articles)
            
            # Now scrape additional sections if needed
            for section in sections:
                # Skip the section if it's already in the base URL
                if section in self.base_url:
                    continue
                    
                section_url = f"https://www.theguardian.com/{section}"
                logger.info(f"Fetching content from additional section: {section_url}")
                section_articles = self._scrape_section(section_url)
                articles.extend(section_articles)
            
        except Exception as e:
            logger.error(f"Error scraping article listings: {str(e)}")
            self.errors.append(f"Error scraping article listings: {str(e)}")
        
        # Remove any duplicate articles (same URL)
        unique_articles = []
        seen_urls = set()
        for article in articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        logger.info(f"Total Guardian articles found: {len(unique_articles)}")
        return unique_articles
    
    def _scrape_section(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrape articles from a specific Guardian section.
        
        Args:
            url: URL of the section to scrape
            
        Returns:
            List of article data dictionaries
        """
        section_articles = []
        
        try:
            soup = self.get_soup(url)
            
            # First try to get article links directly
            logger.info(f"Searching for article links in {url}")
            
            # These are the main article containers in The Guardian's layout
            selectors = [
                'div.fc-item--standard', 
                'div.fc-item', 
                'div.js-snappa-item',
                'div[data-link-name*="article"]',
                'article',
                'a.u-faux-block-link__overlay'
            ]
            
            article_elements = []
            
            # Try each selector
            for selector in selectors:
                elements = soup.select(selector)
                logger.info(f"Found {len(elements)} elements with selector '{selector}'")
                if elements:
                    article_elements.extend(elements)
            
            # Process all found elements
            for i, element in enumerate(article_elements):
                try:
                    logger.info(f"Processing element {i+1}/{len(article_elements)}")
                    article_data = None
                    
                    # If the element is a link
                    if element.name == 'a':
                        article_data = self._extract_from_link(element)
                    # Otherwise treat it as a container
                    else:
                        article_data = self._extract_article_data(element)
                        
                    if article_data:
                        section_articles.append(article_data)
                        logger.info(f"Successfully extracted article: {article_data['title']}")
                except Exception as e:
                    logger.error(f"Error processing element {i+1}: {str(e)}")
            
            # If no articles found using containers, try a direct link approach
            if not section_articles:
                logger.info("No articles found using containers. Trying direct link approach.")
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag.get('href', '')
                    # Check if it's likely an article link
                    if (
                        (
                            '/article/' in href or 
                            any(f'/{section}/' in href for section in ['europe', 'technology', 'business', 'world', 'uk-news']) 
                        ) and
                        not href.endswith('/all') and  # exclude section index pages
                        'live' not in href  # exclude live blogs
                    ):
                        try:
                            article_data = self._extract_from_link(a_tag)
                            if article_data:
                                section_articles.append(article_data)
                                logger.info(f"Found article via direct link: {article_data['title']}")
                        except Exception as e:
                            logger.error(f"Error extracting from link: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error scraping section {url}: {str(e)}")
            
        logger.info(f"Found {len(section_articles)} articles in section {url}")
        return section_articles
    
    def _extract_from_link(self, link_elem: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract article data directly from a link element.
        
        Args:
            link_elem: BeautifulSoup element representing a link
            
        Returns:
            Dictionary with article data, or None if extraction failed
        """
        try:
            url = link_elem.get('href', '')
            if not url:
                return None
                
            # Make sure URL is absolute
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)
                
            # Filter out non-Guardian URLs or non-article pages
            if 'theguardian.com' not in url and not url.startswith('/'):
                return None
                
            # Get title directly from link text or its children
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 10:  # Title should be reasonably long
                return None
                
            logger.debug(f"Processing link: '{title}' - {url}")
            
            # Get parent container for additional info
            parent = link_elem.parent
            
            # Try to find an image using Guardian's specific structure
            image_url = ""
            current = parent
            
            # Look up to 3 levels for image
            for _ in range(3):
                if not current:
                    break
                
                # First try the specific Guardian image structure
                picture = current.select_one('picture.dcr-kunqwb, picture')
                if picture:
                    img = picture.select_one('img')
                    if img and 'src' in img.attrs:
                        image_url = img['src']
                        logger.debug(f"Found image from picture: {image_url}")
                        break
                        
                # Also try direct img elements
                img = current.select_one('img[src]')
                if img:
                    image_url = img['src']
                    logger.debug(f"Found direct image: {image_url}")
                    break
                
                # Try div with data-component="image" or data-gu-name="image"
                div_image = current.select_one('div[data-component="image"], div[data-gu-name="image"]')
                if div_image:
                    img = div_image.select_one('img')
                    if img and 'src' in img.attrs:
                        image_url = img['src']
                        logger.debug(f"Found image from image component: {image_url}")
                        break
                        
                current = current.parent
            
            # Make sure image URL is absolute
            if image_url and not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(self.base_url, image_url)
            
            # Try to get a summary from a paragraph near the link
            summary = ""
            current = parent
            for _ in range(3):  # Check up to 3 levels
                if not current:
                    break
                    
                # Try to find a paragraph
                p = current.select_one('p.fc-item__standfirst, p')
                if p:
                    text = p.get_text(strip=True)
                    if text and text != title and len(text) > 20:
                        summary = text
                        logger.debug(f"Found summary: {summary[:50]}...")
                        break
                
                current = current.parent
            
            # Determine category from the URL and link context
            category = self._extract_category_from_url(url)
            
            return {
                'title': title,
                'url': url,
                'summary': summary,
                'published_at': None,  # Will be extracted from article page
                'image_url': image_url,
                'categories': [category] if category else ['News']
            }
            
        except Exception as e:
            logger.error(f"Error extracting data from link: {str(e)}")
            return None
    
    def _extract_article_data(self, article_elem: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract data from an article element.
        
        Args:
            article_elem: BeautifulSoup element representing an article
            
        Returns:
            Dictionary with article data, or None if extraction failed
        """
        # Find the article link - try multiple approaches
        link_elem = None
        link_selectors = [
            'a.fc-item__link',
            'a.u-faux-block-link__overlay',
            'h3 a',
            'h2 a',
            'a[data-link-name*="article"]',
            'a'
        ]
        
        for selector in link_selectors:
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
            
        # Extract title
        title = link_elem.get_text(strip=True)
        
        # If no title in the link itself, look for headings
        if not title:
            heading_elem = article_elem.select_one('h1, h2, h3, h4, .fc-item__title, .js-headline-text')
            if heading_elem:
                title = heading_elem.get_text(strip=True)
        
        if not title:
            logger.warning(f"No title found for URL: {url}")
            return None
        
        # Extract summary if available
        summary = ""
        summary_elem = article_elem.select_one('.fc-item__standfirst, p')
        if summary_elem:
            summary = summary_elem.get_text(strip=True)
            if summary == title:  # Don't use the title as summary
                summary = ""
        
        # Extract image URL using Guardian's specific structure
        image_url = ""
        
        # Approach 1: Look for picture with class dcr-kunqwb
        picture = article_elem.select_one('picture.dcr-kunqwb, picture')
        if picture:
            img = picture.select_one('img')
            if img and 'src' in img.attrs:
                image_url = img['src']
                logger.debug(f"Found image from picture element: {image_url}")
        
        # Approach 2: Look for any image if approach 1 failed
        if not image_url:
            img = article_elem.select_one('img[src]')
            if img:
                image_url = img['src']
                logger.debug(f"Found direct image: {image_url}")
        
        # Make sure image URL is absolute
        if image_url and not image_url.startswith(('http://', 'https://')):
            image_url = urljoin(self.base_url, image_url)
        
        # Determine category
        category = self._extract_category_from_url(url)
        if not category:
            # Try to find it in the article element
            category_elem = article_elem.select_one('.fc-item__kicker, .fc-item__container')
            if category_elem:
                category_text = category_elem.get_text(strip=True)
                if category_text and category_text != title:
                    category = category_text
        
        return {
            'title': title,
            'url': url,
            'summary': summary,
            'published_at': None,  # Will be extracted from the article page
            'image_url': image_url,
            'categories': [category] if category else ['News']
        }
    
    def _extract_category_from_url(self, url: str) -> Optional[str]:
        """
        Extract the category from a Guardian article URL.
        
        Args:
            url: Article URL
            
        Returns:
            Category name or None if not found
        """
        try:
            # Guardian URLs typically follow this pattern: 
            # https://www.theguardian.com/world/europe/2023/apr/17/article-title
            # or https://www.theguardian.com/technology/2023/apr/17/article-title
            
            # Define category mappings
            category_mappings = {
                'technology': 'Technology',
                'business': 'Business',
                'money': 'Money',
                'environment': 'Environment',
                'world': 'World',
                'europe': 'Europe',
                'uk-news': 'UK News',
                'us-news': 'US News',
                'politics': 'Politics',
                'sport': 'Sport',
                'football': 'Football',
                'science': 'Science',
                'global-development': 'Global Development'
            }
            
            # Extract potential category from URL
            for category_slug, category_name in category_mappings.items():
                if f'/{category_slug}/' in url:
                    return category_name
            
            # If no matching category found, try to extract from URL parts
            parts = url.split('/')
            for part in parts:
                if part in category_mappings:
                    return category_mappings[part]
                
            # For parts not in the mapping, try to format them nicely
            for part in parts:
                if part and part not in ['www.theguardian.com', 'article'] and not re.match(r'^[0-9]{4}$', part) and not re.match(r'^[a-z]{3}$', part):
                    # Convert slug format to Title Case
                    return ' '.join(word.capitalize() for word in part.split('-'))
                
        except Exception as e:
            logger.warning(f"Error extracting category from URL {url}: {str(e)}")
        
        return None
    
    def scrape_article_content(self, url: str) -> str:
        """
        Scrape the full content of a Guardian article as clean text.
        
        Args:
            url: URL of the article
            
        Returns:
            Article content as clean text
        """
        try:
            logger.info(f"Scraping article content from URL: {url}")
            soup = self.get_soup(url)
            
            # Extract article metadata while we're here
            self._extract_article_metadata(url, soup)
            
            # Get the article content
            content_paragraphs = []
            
            # Get the headline - try multiple selectors
            headline_selectors = [
                'h1.dcr-y70mar, h1.dcr-u0152o, h1.dcr-65q7o2', 
                'h1[data-component="headline"]', 
                'h1.content__headline', 
                'h1'
            ]
            
            for selector in headline_selectors:
                headline_elem = soup.select_one(selector)
                if headline_elem:
                    headline_text = headline_elem.get_text(strip=True)
                    content_paragraphs.append(headline_text)
                    logger.debug(f"Found headline: {headline_text}")
                    break
            
            # Try multiple approaches to find the main content
            content_selectors = [
                'div.dcr-1f6fo0p, div.dcr-hzam7a, div.dcr-1fnjjtg', 
                'div[data-component="body"]',
                'div.content__article-body',
                'article[itemprop="articleBody"]',
                'div.article-body-commercial-selector',
                'div.js-article__body'
            ]
            
            for selector in content_selectors:
                content_elems = soup.select(selector)
                if content_elems:
                    logger.info(f"Found {len(content_elems)} content elements with selector '{selector}'")
                    
                    # Process all found content elements
                    for content_elem in content_elems:
                        # Get all paragraphs
                        paragraphs = content_elem.select('p')
                        logger.debug(f"Found {len(paragraphs)} paragraphs")
                        
                        for p in paragraphs:
                            # Skip non-content paragraphs
                            skip_classes = ['byline', 'caption', 'signoff', 'publication']
                            if p.get('class') and any(cls in str(p.get('class')) for cls in skip_classes):
                                continue
                                
                            text = p.get_text(strip=True)
                            if text:
                                content_paragraphs.append(text)
                        
                        # Also get subheadings
                        for heading in content_elem.select('h2, h3'):
                            text = heading.get_text(strip=True)
                            if text:
                                content_paragraphs.append(text)
                    
                    # If we found content, we can break
                    if len(content_paragraphs) > 1:
                        break
            
            # If we still don't have content, try a generic approach
            if len(content_paragraphs) <= 1:  # Only headline or nothing
                logger.warning("No content found using specific selectors. Using generic approach.")
                for p in soup.select('p'):
                    # Skip short paragraphs and likely captions
                    text = p.get_text(strip=True)
                    if text and len(text) > 30:
                        content_paragraphs.append(text)
            
            # Join paragraphs with double newlines
            content = '\n\n'.join(content_paragraphs)
            logger.info(f"Extracted {len(content_paragraphs)} paragraphs of content")
            
            return content
        
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
            # Extract publication date
            date_selectors = [
                'time[datetime]', 
                'time[data-timestamp]',
                '.content__dateline time', 
                '[itemprop="datePublished"]',
                '.dcr-u003f1'
            ]
            
            for selector in date_selectors:
                time_elem = soup.select_one(selector)
                if time_elem:
                    for attr in ['datetime', 'data-timestamp']:
                        if time_elem.has_attr(attr):
                            try:
                                metadata['published_at'] = dateutil.parser.parse(time_elem[attr])
                                break
                            except Exception:
                                pass
                    
                    if not metadata['published_at']:
                        # Try to parse from text
                        date_text = time_elem.get_text(strip=True)
                        try:
                            metadata['published_at'] = dateutil.parser.parse(date_text, fuzzy=True)
                        except Exception:
                            pass
                    
                    if metadata['published_at']:
                        break
            
            # Extract summary
            summary_selectors = [
                'div[data-component="standfirst"]', 
                '.content__standfirst',
                'meta[name="description"]'
            ]
            
            for selector in summary_selectors:
                summary_elem = soup.select_one(selector)
                if summary_elem:
                    if selector == 'meta[name="description"]':
                        metadata['summary'] = summary_elem.get('content', '')
                    else:
                        metadata['summary'] = summary_elem.get_text(strip=True)
                    
                    if metadata['summary']:
                        break
            
            # Extract categories
            category_selectors = [
                'a[data-link-name="article section"]',
                '.content__section-label a',
                'meta[property="article:section"]',
                'ul.dcr-12ctpfx li a'
            ]
            
            for selector in category_selectors:
                if selector.startswith('meta'):
                    meta_elem = soup.select_one(selector)
                    if meta_elem and meta_elem.has_attr('content'):
                        metadata['categories'].append(meta_elem['content'])
                else:
                    for elem in soup.select(selector):
                        text = elem.get_text(strip=True)
                        if text:
                            metadata['categories'].append(text)
            
            # If no categories found, extract from URL
            if not metadata['categories']:
                category = self._extract_category_from_url(url)
                if category:
                    metadata['categories'].append(category)
            
            # Default to 'News' if no categories found
            if not metadata['categories']:
                metadata['categories'].append('News')
            
            # Update article in database
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