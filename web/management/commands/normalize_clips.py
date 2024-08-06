from django.core.management.base import BaseCommand
from web.models import Clip
from web.tasks.clipper_tasks import normalize_clip_audio


class Command(BaseCommand):
    help = "Normalize the audio of all clips in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, help="Limit the number of clips to process"
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        clips = Clip.objects.all()

        if limit:
            clips = clips.order_by("?")[:limit]

        total_clips = clips.count()
        self.stdout.write(f"Starting normalization for {total_clips} clips...")

        for clip in clips:
            normalize_clip_audio.delay(clip.id)
            self.stdout.write(f"Queued normalization task for clip {clip.id}")

        self.stdout.write(
            self.style.SUCCESS(f"Queued normalization tasks for {total_clips} clips")
        )
