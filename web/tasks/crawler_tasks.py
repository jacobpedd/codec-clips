import feedparser
from datetime import datetime
from dateutil import parser as date_parser
from celery import shared_task
from celery.utils.log import get_task_logger
from web.models import Feed, FeedItem
from web.lib.r2 import handle_r2_audio_upload
from web.lib.transcribe import transcribe
from web.lib.parsing import get_duration


logging = get_task_logger(__name__)


@shared_task
def crawl_all_feeds() -> None:
    # Scheduled with beat to run every hour
    feeds = Feed.objects.all()
    for feed in feeds:
        crawl_feed.delay(feed.id)


@shared_task(autoretry_for=(IndexError, KeyError), max_retries=3, retry_backoff=30)
def crawl_feed(feed_id: int) -> None:
    """crawl and parse the RSS feeds."""
    feed = Feed.objects.get(id=feed_id)
    logging.info("[Started] Checking for new episodes from %s ....", feed.name)

    # crawl the RSS feed
    parsed_feed_dict = feedparser.parse(feed.url)

    # Check if feed name or description changed
    if (
        parsed_feed_dict["feed"]["title"] != feed.name
        or parsed_feed_dict["feed"]["description"] != feed.description
    ):
        feed.name = parsed_feed_dict["feed"]["title"]
        feed.description = parsed_feed_dict["feed"]["description"]
        feed.save()
        logging.info(
            "Feed name or description changed, updated feed name and description."
        )

    # Parse the first entry's audio url
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
    feed_item = FeedItem.objects.create(
        name=entry.get("title", "Untitled"),
        body=entry.get("summary", ""),
        audio_url=audio_url,
        audio_bucket_key=audio_bucket_key,
        transcript_bucket_key=transcript_bucket_key,
        duration=(
            get_duration(entry["itunes_duration"]) if "itunes_duration" in entry else 0
        ),
        posted_at=published_date,
        feed=feed,
    )

    logging.info("[Finished] crawld new episode: %s", entry.get("title", "Untitled"))
    return feed_item.id
