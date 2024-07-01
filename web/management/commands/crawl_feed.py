from django.core.management.base import BaseCommand, CommandError
from web.tasks import rss_feed_scrape_task
from web.models import Feed


class Command(BaseCommand):
    help = "Crawl a specific RSS feed by its ID"

    def add_arguments(self, parser):
        parser.add_argument("feed_id", type=int, help="The ID of the feed to crawl")

    def handle(self, *args, **options):
        feed_id = options["feed_id"]

        try:
            Feed.objects.get(id=feed_id)
        except Feed.DoesNotExist:
            raise CommandError(f"Feed with ID {feed_id} does not exist")

        self.stdout.write(
            self.style.SUCCESS(f"Starting to crawl feed with ID {feed_id}")
        )

        try:
            rss_feed_scrape_task(feed_id)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully crawled feed with ID {feed_id}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"An error occurred while crawling feed {feed_id}: {str(e)}"
                )
            )
