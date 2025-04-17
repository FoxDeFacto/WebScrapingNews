"""
Scraper factory module.
"""
from core.models import NewsSource
from .novinky_scraper import NovinkyScraper
from .pravda_scraper import PravdaScraper
from .guardian_scraper import GuardianScraper


def get_scraper_for_source(source: NewsSource):
    """
    Factory function to get the appropriate scraper for a news source.
    
    Args:
        source: NewsSource model instance
        
    Returns:
        Scraper instance for the given source
    
    Raises:
        ValueError: If no scraper is available for the given source
    """
    # Map source slugs to scraper classes
    scraper_map = {
        'novinky': NovinkyScraper,
        'pravda': PravdaScraper,
        'guardian':GuardianScraper
    }
    
    # Get the scraper class based on the source slug
    source_type = source.slug.lower()
    
    # Try to find an exact match
    if source_type in scraper_map:
        return scraper_map[source_type](source)
    
    # Try to find a partial match
    for key, scraper_class in scraper_map.items():
        if key in source_type:
            return scraper_class(source)
    
    # No scraper found
    raise ValueError(f"No scraper available for source: {source.name} (slug: {source.slug})")