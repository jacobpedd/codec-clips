from django.core.management.base import BaseCommand
from web.tasks import crawl_itunes


class Command(BaseCommand):
    help = "Crawl itunes index"

    def handle(self, *args, **options):
        crawl_itunes()
