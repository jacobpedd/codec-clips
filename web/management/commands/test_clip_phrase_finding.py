import os
import json
from django.core.management.base import BaseCommand, CommandError
from web.lib.clipper import refine_clips, suggest_clips
from web.lib.r2 import get_audio_transcript
from web.models import FeedItem


class Command(BaseCommand):
    help = "Test the accuracy of phrase finding on a specific feed item"

    def add_arguments(self, parser):
        parser.add_argument(
            "feed_item_id", type=int, help="The ID of the feed item to process"
        )

    def handle(self, *args, **options):
        feed_item_id = options["feed_item_id"]
        feed_item = FeedItem.objects.get(id=feed_item_id)

        transcript = get_audio_transcript(feed_item.transcript_bucket_key)

        # Save the transcript to the clips folder for debugging
        clips_dir = f"./clips/{feed_item_id}"
        if not os.path.exists(clips_dir):
            os.makedirs(clips_dir)
        with open(f"{clips_dir}/transcript.json", "w") as f:
            f.write(json.dumps(transcript, indent=2))

        clips = suggest_clips(transcript)
        clips = refine_clips(transcript, clips)

        print(f"Found timing for {len(clips)} out of 5 clips")
