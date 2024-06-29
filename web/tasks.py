import feedparser
from datetime import datetime
from dateutil import parser as date_parser
from celery import shared_task
from celery.utils.log import get_task_logger
from web.models import Feed, FeedItem
from web.lib.parsing import get_duration
from web.lib.r2 import handle_r2_upload

logging = get_task_logger(__name__)


@shared_task
def scrape_all_feeds() -> None:
    # Scheduled with beat to run every hour
    feeds = Feed.objects.all()
    for feed in feeds:
        rss_feed_scrape_task.delay(feed.id)


@shared_task(
    bind=True,
    retry_backoff=3,
    retry_kwargs={
        "max_retries": 3,
    },
)
def rss_feed_scrape_task(self, feed_id: int) -> None:
    """Scrape and parse the RSS feeds."""
    feed_obj = Feed.objects.get(id=feed_id)

    if self.request.retries > 0:  # Only when retrying
        logging.info(
            "[Task Retry] Attempt %d/%d",
            self.request.retries,
            self.retry_kwargs["max_retries"],
        )
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
    try:
        audio_bucket_key = handle_r2_upload(audio_url)
    except Exception as e:
        logging.error(f"Failed to handle R2 upload: {str(e)}")
        raise self.retry(exc=e)

    # Create a new FeedItem
    FeedItem.objects.create(
        name=entry.get("title", "Untitled"),
        body=entry.get("summary", ""),
        audio_url=audio_url,
        audio_bucket_key=audio_bucket_key,
        duration=(
            get_duration(entry["itunes_duration"]) if "itunes_duration" in entry else 0
        ),
        posted_at=published_date,
        feed=feed_obj,
    )

    logging.info("[Finished] Scraped new episode: %s", entry.get("title", "Untitled"))
