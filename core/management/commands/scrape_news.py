"""
Management command to scrape news from all active sources.
"""
import logging
import time
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import NewsSource
from scrapers import get_scraper_for_source

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to scrape news from all active sources.
    """
    help = 'Scrape news from all active sources'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--source',
            type=str,
            help='Slug of the news source to scrape (default: all active sources)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Increase output verbosity',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        source_slug = options.get('source')
        verbose = options.get('verbose', False)
        
        # Configure logging
        if verbose:
            logger.setLevel(logging.INFO)
        
        start_time = time.time()
        self.stdout.write(f"Starting news scraping at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get sources to scrape
        if source_slug:
            sources = NewsSource.objects.filter(slug=source_slug, active=True)
            if not sources.exists():
                self.stderr.write(self.style.ERROR(f"No active source found with slug '{source_slug}'"))
                return
        else:
            sources = NewsSource.objects.filter(active=True)
            
        if not sources.exists():
            self.stderr.write(self.style.WARNING("No active news sources found"))
            return
            
        self.stdout.write(f"Found {sources.count()} active source(s) to scrape")
        
        # Scrape each source
        success_count = 0
        error_count = 0
        
        for source in sources:
            try:
                self.stdout.write(f"Scraping {source.name}...")
                
                # Get the appropriate scraper for this source
                scraper = get_scraper_for_source(source)
                
                # Run the scraper
                scraper.scrape()
                
                # Report results
                if scraper.log.success:
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully scraped {source.name}: "
                        f"Found {scraper.articles_found} articles, "
                        f"Added {scraper.articles_added}, "
                        f"Updated {scraper.articles_updated}"
                    ))
                else:
                    error_count += 1
                    self.stderr.write(self.style.ERROR(
                        f"Error scraping {source.name}: {scraper.log.errors}"
                    ))
                    
            except Exception as e:
                error_count += 1
                self.stderr.write(self.style.ERROR(f"Error scraping {source.name}: {str(e)}"))
        
        # Report overall results
        elapsed_time = time.time() - start_time
        self.stdout.write(f"Finished scraping in {elapsed_time:.2f} seconds")
        self.stdout.write(f"Success: {success_count}, Errors: {error_count}")