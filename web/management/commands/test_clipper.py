import os
import shutil
from django.core.management.base import BaseCommand
from web.lib.clipper import generate_clips
from web.lib.clipper.transcript_utils import format_transcript_view
from web.lib.clipper.clip_audio import save_clip_audio
from web.lib.r2 import download_audio_file, get_audio_transcript
from web.models import FeedItem


class Command(BaseCommand):
    help = "Test generate_clips_from_feed_item function with a specific feed item ID"

    def add_arguments(self, parser):
        parser.add_argument(
            "feed_item_id", type=int, help="The ID of the feed item to process"
        )

    def handle(self, *args, **options):
        feed_item_id = options["feed_item_id"]
        self.stdout.write(
            self.style.SUCCESS(f"Testing with feed item ID: {feed_item_id}")
        )
        try:
            # Save the clips to a clips folder
            clips_dir = f"./clips/{feed_item_id}"
            if not os.path.exists(clips_dir):
                os.makedirs(clips_dir)

            feed_item = FeedItem.objects.get(id=feed_item_id)
            transcript = get_audio_transcript(feed_item.transcript_bucket_key)
            if not transcript:
                raise ValueError("Transcript not found")

            # Download the audio file from R2 to the disk
            audio_file_path = f"{clips_dir}/{feed_item.audio_bucket_key}"
            if not os.path.exists(audio_file_path):
                download_audio_file(feed_item.audio_bucket_key, clips_dir)
                print(f"Downloaded audio file to {audio_file_path}")

            # Remove all existing directories in the clips folder
            for clip_dir in os.listdir(clips_dir):
                clip_dir_path = os.path.join(clips_dir, clip_dir)
                if os.path.isdir(clip_dir_path):
                    shutil.rmtree(clip_dir_path)

            clips = generate_clips(transcript, max_clips=3)
            for clip in clips:
                # Save the clip to a clips folder
                clip_dir = f"{clips_dir}/{clip['name']}"
                if not os.path.exists(clip_dir):
                    os.makedirs(clip_dir)
                save_clip_audio(clip_dir, audio_file_path, clip)
                print(f"Saved clip: {clip['name']}")

                # Save the clip transcript
                with open(f"{clip_dir}/transcript.md", "w") as f:
                    f.write(
                        format_transcript_view(
                            transcript, clip["quote"], clip, 100, 100
                        )
                    )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
