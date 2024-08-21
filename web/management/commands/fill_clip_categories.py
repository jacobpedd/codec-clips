from django.core.management.base import BaseCommand
from web.models import Clip
from web.tasks import update_clip_categories


class Command(BaseCommand):
    help = "Start Celery jobs to update categories for all clips in batches"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of clips to process",
            default=None,
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            help="Number of tasks to create per batch",
            default=100,
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        batch_size = options["batch_size"]

        clips = Clip.objects.filter(clipcategoryscore__isnull=True)
        if limit:
            clips = clips[:limit]
        total_clips = clips.count()

        self.stdout.write(
            f"Starting category update for {total_clips} clips, creating tasks in batches of {batch_size}..."
        )

        clip_ids = list(clips.values_list("id", flat=True))

        # Batch the creation of tasks
        for i in range(0, total_clips, batch_size):
            batch = clip_ids[i : i + batch_size]
            for clip_id in batch:
                update_clip_categories.delay(clip_id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully initiated category update tasks for {total_clips} clips in {total_clips // batch_size + 1} batches."
            )
        )
