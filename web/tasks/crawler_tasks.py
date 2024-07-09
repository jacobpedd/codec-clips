import re
from assemblyai import TranscriptError
import requests
import datetime
from celery import shared_task, group
from django.db import IntegrityError
from celery.utils.log import get_task_logger
from web.lib.crawler import (
    crawl_itunes_podcast_links,
    crawl_itunes_ratings,
    crawl_rss_feed,
    itunes_podcast_lookup,
)
from web.models import Feed, FeedItem
from web.lib.r2 import handle_r2_audio_upload
from web.lib.transcribe import transcribe
from web.lib.parsing import get_duration

logging = get_task_logger(__name__)


# NOTE: Eventually, to scrape all podcasts, start at the categories page and crawl all links
ITUNES_URLS = [
    "https://podcasts.apple.com/us/genre/podcasts-business/id1321",
    "https://podcasts.apple.com/us/genre/podcasts-comedy/id1303",
    "https://podcasts.apple.com/us/genre/podcasts-news/id1489",
    "https://podcasts.apple.com/us/genre/podcasts-sports/id1545",
    "https://podcasts.apple.com/us/genre/podcasts-technology/id1318",
]


@shared_task
def crawl_itunes() -> str:
    itunes_podcast_links = []
    for url in ITUNES_URLS:
        logging.info(f"Crawling {url}")
        podcast_links = crawl_itunes_podcast_links(url)
        if podcast_links:
            itunes_podcast_links.extend(podcast_links)
        else:
            logging.warning(f"No podcast links found in {url}")

    # Remove duplicate URLs
    itunes_podcast_links = list(set(itunes_podcast_links))

    # Create a group of tasks for processing each podcast
    tasks = group(
        crawl_itunes_podcast.s(podcast_url) for podcast_url in itunes_podcast_links
    )

    # Execute the group of tasks without waiting
    result = tasks.apply_async()

    # Store the group result ID for potential later use
    group_result_id = result.id

    logging.info(
        f"Started processing {len(itunes_podcast_links)} podcasts. Group result ID: {group_result_id}"
    )
    return group_result_id


@shared_task(
    autoretry_for=(requests.RequestException, KeyError),
    max_retries=3,
    retry_backoff=30,
    rate_limit="20/m",
)
def crawl_itunes_podcast(podcast_url):
    match = re.search(r"/id(\d+)", podcast_url)
    if not match:
        logging.error(f"Could not extract podcast ID from URL: {podcast_url}")
        return

    podcast_id = match.group(1)

    try:
        total_ratings = crawl_itunes_ratings(podcast_url)
        if total_ratings == 0:
            logging.warning(f"No ratings found for podcast: {podcast_url}")
            return

        feed_url, feed_name = itunes_podcast_lookup(podcast_id)
        if not feed_url:
            logging.warning(f"No feed URL found for podcast ID {podcast_id}")
            return

        try:
            feed, created = Feed.objects.get_or_create(
                url=feed_url,
                defaults={
                    "name": feed_name,
                    "description": "",
                    "total_itunes_ratings": total_ratings,
                },
            )
            if created:
                logging.info(f"Added new feed: {feed.name}")
            else:
                feed.total_itunes_ratings = total_ratings
                feed.save()
                logging.info(f"Updated existing feed: {feed.name}")
        except IntegrityError:
            logging.info(f"Feed already exists: {feed_name}")

    except requests.RequestException as e:
        logging.error(
            f"Failed to fetch podcast page or lookup iTunes ID {podcast_id}: {str(e)}"
        )
    except Exception as e:
        logging.error(f"Error processing podcast {podcast_url}: {str(e)}")


@shared_task
def crawl_top_feeds() -> None:
    # Scheduled with beat to run every hour
    feeds = Feed.objects.order_by("-total_itunes_ratings")[:250]

    # Create a group of tasks for processing each feed
    tasks = group(
        crawl_feed.s(feed.id) for feed in feeds if feed.url.startswith("https://")
    )

    # Execute the group of tasks without waiting
    result = tasks.apply_async()

    # Log the group result ID for potential later use
    group_result_id = result.id

    logging.info(
        f"Started processing {len(feeds)} feeds. Group result ID: {group_result_id}"
    )
    return group_result_id


@shared_task(
    autoretry_for=(IndexError, KeyError, AttributeError),
    max_retries=3,
    retry_backoff=30,
)
def crawl_feed(feed_id: int) -> None:
    """crawl and parse the RSS feeds."""
    feed = Feed.objects.get(id=feed_id)
    logging.info("[Started] Checking for new episodes from %s ....", feed.name)

    # Crawl the RSS feed
    feed_data, entry_data = crawl_rss_feed(feed.url)

    # Check if feed name or description changed
    if feed_data["title"] != feed.name or feed_data["description"] != feed.description:
        feed.name = feed_data["title"]
        feed.description = feed_data["description"]
        feed.save()
        logging.info(
            "Feed name or description changed, updated feed name and description."
        )

    if entry_data["audio_url"] is None:
        logging.warning(f"Entry has no audio URL: {entry_data}")
        return

    # Skip if it is already in the database
    if FeedItem.objects.filter(audio_url=entry_data["audio_url"]).first():
        logging.info("[Finished] No new episodes found.")
        return

    # Skip if episode is older than 1 week
    published_datetime = datetime.datetime(*entry_data["published_parsed"][:6])
    if (datetime.datetime.now() - published_datetime).days > 7:
        logging.info(f"Entry is older than 1 week: {entry_data['published_parsed']}")
        return

    # Trigger the crawl_feed_item task for the new feed item
    task_id = f"crawl_feed_item-{entry_data['audio_url']}"
    crawl_feed_item.apply_async(args=[feed.id, entry_data], task_id=task_id)


@shared_task(
    autoretry_for=(TranscriptError,),
    max_retries=3,
    retry_backoff=30,
    rate_limit="100/m",
)
def crawl_feed_item(feed_id: int, entry_data: dict) -> FeedItem:
    # Parse the entry's audio url and published date
    audio_url = entry_data["audio_url"]
    published_datetime = datetime.datetime(*entry_data["published_parsed"][:6])

    # Check if the audio file already exists in the database
    feed_item = FeedItem.objects.filter(audio_url=audio_url).first()
    if feed_item:
        logging.info(f"Feed item already exists: {feed_item.name}")
        return feed_item.id

    # Save audio file to R2
    logging.info(f"Saving audio file to R2: {audio_url}")
    audio_bucket_key = handle_r2_audio_upload(audio_url)

    # Transcribe the audio file
    logging.info(f"Transcribing: {audio_url}")
    transcript_bucket_key = transcribe(audio_bucket_key)

    # Create a new FeedItem
    feed_item = FeedItem.objects.create(
        name=entry_data.get("title", "Untitled"),
        body=entry_data.get("summary", ""),
        audio_url=audio_url,
        audio_bucket_key=audio_bucket_key,
        transcript_bucket_key=transcript_bucket_key,
        duration=get_duration(entry_data.get("itunes_duration", "0:00")),
        posted_at=published_datetime,
        feed_id=feed_id,
    )
    return feed_item.id
