from django.core.management.base import BaseCommand, CommandError
from web.tasks import crawl_top_feeds


class Command(BaseCommand):
    help = "Crawl top RSS feeds"

    def handle(self, *args, **options):
        crawl_top_feeds()
