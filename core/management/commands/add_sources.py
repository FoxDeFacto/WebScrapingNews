"""
Management command to add new news sources to the database.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from core.models import NewsSource


class Command(BaseCommand):
    """
    Django management command to add new news sources to the database.
    """
    help = 'Add new news sources to the database'
    
    def handle(self, *args, **options):
        """Execute the command."""
        # Define the sources to add
        sources = [
            {
                'name': 'The Guardian',
                'slug': 'guardian',
                'base_url': 'https://www.theguardian.com/europe',
                'description': 'The Guardian is a British daily newspaper with a European edition covering news, politics, business, and more.',
                'language': 'en',
            },
            {
                'name': 'Novinky',
                'slug': 'novinky',
                'base_url': 'https://www.novinky.cz/',
                'description': 'Novinky is one of the most popular Czech news portals providing up-to-date news from the Czech Republic and around the world.',
                'language': 'cs',
            },
            {
                'name': 'Pravda',
                'slug': 'pravda',
                'base_url': 'https://www.pravda.com.ua/',
                'description': 'Pravda is a leading Ukrainian online newspaper covering national and international news, politics, and current events.',
                'language': 'uk',
            },
        ]
        
        # Add each source if it doesn't already exist
        for source_data in sources:
            slug = source_data.get('slug', slugify(source_data['name']))
            source, created = NewsSource.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': source_data['name'],
                    'base_url': source_data['base_url'],
                    'description': source_data.get('description', ''),
                    'language': source_data.get('language', 'en'),
                    'active': True,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"Added new source: {source.name}"))
            else:
                # Update existing source
                source.name = source_data['name']
                source.base_url = source_data['base_url']
                source.description = source_data.get('description', '')
                source.language = source_data.get('language', 'en')
                source.save()
                self.stdout.write(self.style.WARNING(f"Updated existing source: {source.name}"))
        
        self.stdout.write(self.style.SUCCESS("Finished adding news sources"))