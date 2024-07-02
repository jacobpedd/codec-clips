from django.core.management.base import BaseCommand
from django.db import transaction
from web.models import Clip, FeedItem
from web.tasks import generate_clips_from_feed_item


class Command(BaseCommand):
    help = "Deletes all existing clips and regenerates them for all feed items"

    def handle(self, *args, **options):
        self.stdout.write("Starting clip regeneration process...")

        try:
            with transaction.atomic():
                # Delete all existing clips
                clip_count = Clip.objects.count()
                Clip.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {clip_count} existing clips")
                )

                # Get all feed items
                feed_items = FeedItem.objects.all()
                feed_item_count = feed_items.count()

                # Start async tasks to generate clips for each feed item
                for feed_item in feed_items:
                    generate_clips_from_feed_item.delay(feed_item.id)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Started clip generation tasks for {feed_item_count} feed items"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
            return

        self.stdout.write(
            self.style.SUCCESS("Clip regeneration process initiated successfully")
        )
