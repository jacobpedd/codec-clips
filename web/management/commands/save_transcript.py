from django.core.management.base import BaseCommand
from web.lib.clipper.transcript_utils import (
    format_transcript_prompt,
)
from web.lib.r2 import get_audio_transcript
from web.models import FeedItem


class Command(BaseCommand):
    help = "Download and format the transcript for a specific feed item"

    def add_arguments(self, parser):
        parser.add_argument(
            "--feed_item_id", type=int, help="The ID of the feed item to process"
        )
        parser.add_argument(
            "--out",
            type=str,
            help="The path to save the transcript to",
        )

    def handle(self, *args, **options):
        output_path = options["out"]
        feed_item_id = options["feed_item_id"]
        feed_item = FeedItem.objects.get(id=feed_item_id)

        transcript = get_audio_transcript(feed_item.transcript_bucket_key)
        transcript_string, _ = format_transcript_prompt(transcript)

        with open(output_path, "w") as f:
            f.write(transcript_string)
