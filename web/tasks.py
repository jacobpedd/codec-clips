import feedparser
from celery import shared_task
from celery.utils.log import get_task_logger
from web.models import Feed

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
    logging.info("[Started] Scraping data from %s ....", feed_obj.url)
    parsed_feed_dict = feedparser.parse(feed_obj.url)

    # ...
    # Code to parse our feed and update "feed_obj"
    # ...

    logging.info("[Finished] Data from %s was scraped.", feed_obj.url)
