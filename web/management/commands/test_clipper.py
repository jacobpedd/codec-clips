import json
import os
from django.core.management.base import BaseCommand
import ffmpeg
from web.lib.clipper import generate_clips, refine_clips, save_clip_audio, suggest_clips
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

        # Save the clips to a clips folder
        clip_dir = f"./clips/{feed_item_id}"
        if not os.path.exists(clip_dir):
            os.makedirs(clip_dir)

        try:
            feed_item = FeedItem.objects.get(id=feed_item_id)
            transcript = get_audio_transcript(feed_item.transcript_bucket_key)
            if not transcript:
                raise ValueError("Transcript not found")
            # Save the transcript to a clips folder
            transcript_path = f"{clip_dir}/{feed_item.transcript_bucket_key}"
            with open(transcript_path, "w") as f:
                f.write(json.dumps(transcript, indent=2))

            clips = suggest_clips(transcript)

            # Download the audio file from R2 to the disk
            audio_file_path = f"{clip_dir}/{feed_item.audio_bucket_key}"
            if not os.path.exists(audio_file_path):
                download_audio_file(feed_item.audio_bucket_key, clip_dir)
                print(f"Downloaded audio file to {audio_file_path}")

            # Save the clips to a clips folder
            for clip in clips:
                sug_clip_dir = f"{clip_dir}/suggested"
                if not os.path.exists(sug_clip_dir):
                    os.makedirs(sug_clip_dir)
                save_clip_audio(sug_clip_dir, audio_file_path, clip)
                print(f"Suggested clip: {clip.name}")

            clips = refine_clips(transcript, clips)
            for clip in clips:
                ref_clip_dir = f"{clip_dir}/refined"
                if not os.path.exists(ref_clip_dir):
                    os.makedirs(ref_clip_dir)
                save_clip_audio(ref_clip_dir, audio_file_path, clip)
                print(f"Refined clip: {clip.name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
