# core/management/commands/reset_db.py
from django.core.management.base import BaseCommand
from core.models import Article, Category, ScrapingLog

class Command(BaseCommand):
    help = 'Reset the database by deleting all articles, categories, and scraping logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-sources',
            action='store_true',
            help='Keep news sources when resetting',
        )

    def handle(self, *args, **options):
        # Delete all articles first (to avoid foreign key constraints)
        article_count = Article.objects.count()
        Article.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {article_count} articles'))

        # Delete all categories
        category_count = Category.objects.count()
        Category.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {category_count} categories'))

        # Delete all scraping logs
        log_count = ScrapingLog.objects.count()
        ScrapingLog.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {log_count} scraping logs'))

        # Keep news sources if requested
        if not options['keep-sources']:
            from core.models import NewsSource
            source_count = NewsSource.objects.count()
            NewsSource.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {source_count} news sources'))
            self.stdout.write(self.style.WARNING('Database reset complete. You will need to recreate news sources.'))
        else:
            self.stdout.write(self.style.SUCCESS('Database reset complete. News sources were preserved.'))