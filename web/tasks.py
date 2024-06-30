import feedparser
from datetime import datetime
from dateutil import parser as date_parser
from celery import shared_task
from celery.utils.log import get_task_logger
from web.lib.transcribe import transcribe
from web.models import Clip, Feed, FeedItem
from web.lib.parsing import get_duration
from web.lib.clipper import generate_clips, generate_clips_audio
from web.lib.r2 import handle_r2_audio_upload

logging = get_task_logger(__name__)


@shared_task
def scrape_all_feeds() -> None:
    # Scheduled with beat to run every hour
    feeds = Feed.objects.all()
    for feed in feeds:
        rss_feed_scrape_task.delay(feed.id)


@shared_task
def rss_feed_scrape_task(feed_id: int) -> None:
    """Scrape and parse the RSS feeds."""
    feed_obj = Feed.objects.get(id=feed_id)
    logging.info("[Started] Checking for new episodes from %s ....", feed_obj.name)

    # Parse the first entry's audio url
    parsed_feed_dict = feedparser.parse(feed_obj.url)
    entry = parsed_feed_dict["entries"][0]
    audio_url = entry["enclosures"][0]["href"]

    # Check if it is already in the database
    if FeedItem.objects.filter(audio_url=audio_url).first():
        logging.info("[Finished] No new episodes found.")
        return

    # Parse the published date
    try:
        published_date = date_parser.parse(entry.get("published", ""))
    except (ValueError, TypeError):
        published_date = datetime.now()

    # Handle R2 upload
    audio_bucket_key = handle_r2_audio_upload(audio_url)

    # Transcribe the audio file
    logging.info("Transcribing %s ....", audio_url)
    transcript_bucket_key = transcribe(audio_bucket_key)

    # Create a new FeedItem
    FeedItem.objects.create(
        name=entry.get("title", "Untitled"),
        body=entry.get("summary", ""),
        audio_url=audio_url,
        audio_bucket_key=audio_bucket_key,
        transcript_bucket_key=transcript_bucket_key,
        duration=(
            get_duration(entry["itunes_duration"]) if "itunes_duration" in entry else 0
        ),
        posted_at=published_date,
        feed=feed_obj,
    )

    logging.info("[Finished] Scraped new episode: %s", entry.get("title", "Untitled"))


# NOTE: This function is triggered from signals.py when a new feed item is created
@shared_task
def generate_clips_from_feed_item(feed_item_id: int) -> None:
    feed_item = FeedItem.objects.get(id=feed_item_id)

    # Generate clips with LLM
    clips = generate_clips(feed_item.transcript_bucket_key)

    # Create clip audio files
    # TODO: Looks like clip ends aren't lining up with where the LLM instructs it to
    clip_audio_bucket_keys = generate_clips_audio(feed_item.audio_bucket_key, clips)

    # Save clips to models
    for clip, clip_audio_bucket_key in zip(clips, clip_audio_bucket_keys):
        Clip.objects.create(
            name=clip.name,
            body="",
            start_time=clip.start,
            end_time=clip.end,
            audio_bucket_key=clip_audio_bucket_key,
            feed_item=feed_item,
        )

    logging.info("[Finished] Generating clips for feed item: %s", feed_item.name)


@shared_task
def add_missing_clips() -> None:
    # Add clips to all feed items that don't have any clips
    feed_items = FeedItem.objects.filter(clips__isnull=True)
    for feed_item in feed_items:
        generate_clips_from_feed_item.delay(feed_item.id)
