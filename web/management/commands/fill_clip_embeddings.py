from django.core.management.base import BaseCommand
from web.models import Clip
from web.tasks.clipper_tasks import update_clip_embedding


class Command(BaseCommand):
    help = "Initiates the migration of all clips to use the new embedding field"

    def handle(self, *args, **options):
        self.stdout.write("Starting clip embedding migration...")

        try:
            # Get all clips
            clips = Clip.objects.all()
            total_clips = clips.count()

            self.stdout.write(f"Found {total_clips} clips to process")

            # Kick off Celery tasks for all clips
            for clip in clips:
                update_clip_embedding.delay(clip.id)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Initiated embedding update tasks for {total_clips} clips"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Clip embedding migration tasks have been queued successfully"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
