from django.core.management.base import BaseCommand
from django.db import transaction
from web.models import Clip, FeedItem
from web.tasks import generate_clips_from_feed_item


class Command(BaseCommand):
    help = "Deletes all clips for a given feed item and regenerates them"

    def add_arguments(self, parser):
        parser.add_argument(
            "feed_item_id",
            type=int,
            help="The ID of the feed item to regenerate clips for",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting clip regeneration process...")

        try:
            with transaction.atomic():
                # Delete all existing clips for the feed item
                feed_item_id = options["feed_item_id"]
                feed_item = FeedItem.objects.get(id=feed_item_id)
                clip_count = Clip.objects.filter(feed_item=feed_item).count()
                Clip.objects.filter(feed_item=feed_item).delete()
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {clip_count} existing clips")
                )

                # Start async task to generate clips for the feed item
                generate_clips_from_feed_item.delay(feed_item.id)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Started clip generation tasks for {feed_item.name}"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
            return

        self.stdout.write(
            self.style.SUCCESS("Clip regeneration process initiated successfully")
        )
