from django.core.management.base import BaseCommand, CommandError
from web.tasks import crawl_all_feeds
from web.models import Feed


class Command(BaseCommand):
    help = "Crawl all RSS feeds"

    def handle(self, *args, **options):
        crawl_all_feeds()
