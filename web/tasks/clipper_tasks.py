from celery import shared_task
from celery.utils.log import get_task_logger
from web.lib.clipper import generate_clips, generate_clips_audio
from web.lib.r2 import get_audio_transcript
from web.models import FeedItem, Clip

logging = get_task_logger(__name__)


# NOTE: This function is triggered from signals.py when a new feed item is created
@shared_task(rate_limit="10/m")
def generate_clips_from_feed_item(feed_item_id: int) -> None:
    feed_item = FeedItem.objects.get(id=feed_item_id)

    # Generate clips with LLM
    transcript = get_audio_transcript(feed_item.transcript_bucket_key)
    clips = generate_clips(transcript, max_clips=3)

    # Create clip audio files
    clip_audio_bucket_keys = generate_clips_audio(feed_item.audio_bucket_key, clips)

    # Save clips to models
    for clip, clip_audio_bucket_key in zip(clips, clip_audio_bucket_keys):
        Clip.objects.create(
            name=clip["name"],
            body="",
            summary=clip["summary"],
            start_time=clip["start"],
            end_time=clip["end"],
            audio_bucket_key=clip_audio_bucket_key,
            feed_item=feed_item,
        )

    logging.info("[Finished] Generating clips for feed item: %s", feed_item.name)
