from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Count, OuterRef, Exists
from web.models import Clip, ClipTopicScore, ClipCategoryScore
from web.tasks.clipper_tasks import run_clip_tagger


class Command(BaseCommand):
    help = "Fill topics and categories for clips without them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clip_id",
            type=int,
            help="The ID of a specific clip to process",
            required=False,
        )
        parser.add_argument(
            "--nearest_neighbors",
            type=int,
            default=40,
            help="The number of nearest neighbors to consider for evaluation",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of clips to process",
            default=None,
        )
        parser.add_argument(
            "--batch_size",
            type=int,
            help="Number of tasks to create per batch",
            default=100,
        )

    def handle(self, *args, **options):
        clip_id = options.get("clip_id")
        nearest_neighbors = options["nearest_neighbors"]
        limit = options["limit"]
        batch_size = options["batch_size"]

        if clip_id:
            self.process_single_clip(clip_id, nearest_neighbors)
        else:
            self.process_clips_in_batches(nearest_neighbors, limit, batch_size)

    def process_single_clip(self, clip_id, nearest_neighbors):
        try:
            clip = Clip.objects.get(id=clip_id)
        except Clip.DoesNotExist:
            raise CommandError(f"Clip with ID {clip_id} does not exist")

        self.stdout.write(
            self.style.SUCCESS(f"\nProcessing Clip: {clip.name} (ID: {clip.id})")
        )
        self.stdout.write("=" * 50)

        result = run_clip_tagger.delay(clip.id, nearest_neighbors)
        self.stdout.write(f"Topic and category update task result: {result}")

    def process_clips_in_batches(self, nearest_neighbors, limit, batch_size):
        clips = (
            Clip.objects.annotate(
                has_topic_scores=Exists(
                    ClipTopicScore.objects.filter(clip=OuterRef("pk"))
                ),
                has_category_scores=Exists(
                    ClipCategoryScore.objects.filter(clip=OuterRef("pk"))
                ),
            )
            .filter(Q(has_topic_scores=False) | Q(has_category_scores=False))
            .order_by("?")
        )

        if limit:
            clips = clips[:limit]

        total_clips = clips.count()

        self.stdout.write(
            f"Starting topic and category update for {total_clips} clips without topics or categories, creating tasks in batches of {batch_size}..."
        )

        clip_ids = list(clips.values_list("id", flat=True))

        # Batch the creation of tasks
        for i in range(0, total_clips, batch_size):
            batch = clip_ids[i : i + batch_size]
            for clip_id in batch:
                run_clip_tagger.delay(clip_id, nearest_neighbors)

            self.stdout.write(
                f"Initiated tasks for clips {i+1} to {min(i+batch_size, total_clips)}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully initiated topic and category update tasks for {total_clips} clips in {(total_clips - 1) // batch_size + 1} batches."
            )
        )

    def get_random_clip(self):
        random_clip = (
            Clip.objects.filter(
                Q(feed_item__transcript_bucket_key__isnull=False)
                & ~Q(feed_item__transcript_bucket_key="")
            )
            .order_by("?")
            .first()
        )
        if not random_clip:
            raise CommandError("No clips with transcripts found in the database")
        return random_clip
