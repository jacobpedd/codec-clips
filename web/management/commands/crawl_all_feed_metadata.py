from django.core.management.base import BaseCommand
from web.models import Feed
from web.tasks import crawl_feed


class Command(BaseCommand):
    help = "Crawl all RSS feeds without crawling episodes"

    def handle(self, *args, **options):
        feeds = Feed.objects.all()
        total_feeds = feeds.count()

        self.stdout.write(f"Starting to crawl {total_feeds} feeds...")

        for index, feed in enumerate(feeds, start=1):
            self.stdout.write(f"Crawling feed {index}/{total_feeds}: {feed.name}")
            crawl_feed.delay(feed.id, crawl_episodes=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully initiated crawling for {total_feeds} feeds."
            )
        )
