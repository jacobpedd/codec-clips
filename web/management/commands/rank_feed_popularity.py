from django.core.management.base import BaseCommand
from web.tasks import rank_all_feeds_popularity


class Command(BaseCommand):
    help = "Rank feeds popularity"

    def handle(self, *args, **options):
        rank_all_feeds_popularity.delay()
