import re
from assemblyai import TranscriptError
import requests
import datetime
from celery import shared_task, group
from django.db import IntegrityError, transaction
from celery.utils.log import get_task_logger
from web.lib.crawler import (
    crawl_itunes_podcast_links,
    crawl_itunes_ratings,
    crawl_rss_feed,
    itunes_podcast_lookup,
)
from web.lib.embed import get_embedding
from django.contrib.auth.models import User
from web.models import Feed, FeedItem, FeedTopic, FeedUserInterest
from django.db.models import (
    F,
    Case,
    When,
    FloatField,
    Avg,
)
from pgvector.django import CosineDistance, L2Distance
from web.lib.r2 import handle_r2_audio_upload, has_artwork, save_artwork
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
    "https://podcasts.apple.com/us/genre/podcasts-history/id1487",
    "https://podcasts.apple.com/us/genre/podcasts-society-culture/id1324",
    "https://podcasts.apple.com/us/genre/podcasts-tv-film/id1309",
    "https://podcasts.apple.com/us/genre/podcasts-science/id1533",
    "https://podcasts.apple.com/us/genre/podcasts-education/id1304",
    "https://podcasts.apple.com/us/genre/podcasts-true-crime/id1488",
    "https://podcasts.apple.com/us/genre/podcasts-arts/id1301",
    "https://podcasts.apple.com/us/genre/podcasts-health-fitness/id1512",
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
        # Raise the exception to retry the task
        raise e
    except Exception as e:
        logging.error(f"Error processing podcast {podcast_url}: {str(e)}")


@shared_task
def crawl_top_feeds() -> None:
    # Scheduled with beat to run every hour
    feeds = []

    # Get the top 500 feeds by itunes ratings
    top_feeds = (
        Feed.objects.filter(is_english=True)
        .order_by("-total_itunes_ratings")[:500]
        .values_list("id", flat=True)
    )

    # Get the top 500 feeds recommended for each user
    feed_scores = {}
    total_scores = {}
    count_scores = {}

    # Use iterator() for memory efficiency
    for user in User.objects.iterator():
        # Get average embedding of feeds the user is interested in
        avg_embedding = FeedUserInterest.objects.filter(
            user=user, is_interested=True
        ).aggregate(Avg("feed__topic_embedding"))["feed__topic_embedding__avg"]

        if avg_embedding is None:
            continue

        # Get recommended feeds
        zero_vector = [0.0] * len(avg_embedding)
        user_feed_scores = (
            Feed.objects.filter(is_english=True)
            .exclude(id__in=top_feeds)  # Exclude feeds already in top feeds
            .annotate(
                feed_zero_distance=L2Distance("topic_embedding", zero_vector),
                similarity=CosineDistance("topic_embedding", avg_embedding),
                score=Case(
                    When(
                        similarity__isnull=False,
                        then=(1 - F("similarity")) + F("popularity_percentile") * 0.25,
                    ),
                    default=F("popularity_percentile"),
                    output_field=FloatField(),
                ),
            )
            .filter(feed_zero_distance__gt=0)
            .order_by("-score")[:500]
            .values("id", "score")
        )

        for feed in user_feed_scores:
            feed_id, score = feed["id"], feed["score"]
            if feed_id not in feed_scores:
                feed_scores[feed_id] = [score]
                total_scores[feed_id] = score
                count_scores[feed_id] = 1
            else:
                feed_scores[feed_id].append(score)
                total_scores[feed_id] += score
                count_scores[feed_id] += 1

    # Calculate average scores and sort
    avg_scores = {
        feed_id: total_scores[feed_id] / count_scores[feed_id]
        for feed_id in feed_scores
    }
    sorted_feed_scores = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)

    # Take the top 500 scored feeds for the user base
    top_user_feeds = [feed_id for feed_id, _ in sorted_feed_scores[:500]]

    # Combine top_feeds and top_user_feeds
    feeds = list(set(top_feeds) | set(top_user_feeds))

    # Create a group of tasks for processing each feed
    tasks = group(crawl_feed.s(feed_id) for feed_id in feeds)

    # Execute the group of tasks without waiting
    result = tasks.apply_async()

    # Log the group result ID for potential later use
    group_result_id = result.id

    logging.info(
        f"Started processing {len(feeds)} feeds. Group result ID: {group_result_id}"
    )
    return group_result_id


@shared_task(
    autoretry_for=(IndexError, KeyError, AttributeError, requests.HTTPError),
    max_retries=3,
    retry_backoff=30,
)
def crawl_feed(feed_id: int, crawl_episodes: bool = True) -> None:
    """crawl and parse the RSS feeds."""
    feed = Feed.objects.prefetch_related("topics").get(id=feed_id)
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

    # Check if feed language changed
    if feed_data["language"] != feed.language and feed.is_english == False:
        feed.language = feed_data["language"]
        feed.is_english = "en" in feed.language.lower()
        feed.save()
        logging.info("Feed language changed, updated feed language and is_english.")

    # Check if feed topics changed and bulk create new topics
    if "topics" in feed_data:
        existing_topics = set(feed.topics.values_list("text", flat=True))
        new_topics = set(feed_data["topics"]) - existing_topics

        if new_topics:
            with transaction.atomic():
                FeedTopic.objects.bulk_create(
                    [FeedTopic(feed=feed, text=topic) for topic in new_topics],
                    ignore_conflicts=True,
                )

                # Calculate topic embeddings
                text = " ".join(list(set(feed_data["topics"])))
                if text.strip() == "":
                    print("Empty topic text")
                else:
                    topic_embedding = get_embedding(text)

                    # Save the topic embedding
                    feed.topic_embedding = topic_embedding
                    feed.save()

            logging.info(f"Added {len(new_topics)} new topics to feed: {feed.name}")

    # Check if artwork changed
    artwork_bucket_key = has_artwork(feed_data["artwork_url"])
    if artwork_bucket_key is None or feed.artwork_bucket_key != artwork_bucket_key:
        if artwork_bucket_key is None:
            print("Downloading artwork")
            artwork_bucket_key = save_artwork(feed_data["artwork_url"])
        feed.artwork_bucket_key = artwork_bucket_key
        feed.save()
        print("Saved artwork to database")

    if not crawl_episodes:
        logging.info("[Finished] Crawling feed episodes disabled.")
        return

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


@shared_task
def recalculate_feed_embedding_and_topics(feed_id: int) -> None:
    try:
        feed = Feed.objects.get(id=feed_id)

        # Recrawl the RSS feed to get updated topics
        feed_data, _ = crawl_rss_feed(feed.url)

        if "topics" in feed_data:
            with transaction.atomic():
                # Clear existing topics
                FeedTopic.objects.filter(feed=feed).delete()

                # Create new topics
                new_topics = [
                    FeedTopic(feed=feed, text=topic)
                    for topic in set(feed_data["topics"])
                ]
                FeedTopic.objects.bulk_create(new_topics)

                # Calculate new embedding
                topic_text = " ".join(feed_data["topics"])
                new_embedding = get_embedding(topic_text)

                # Update feed with new embedding
                feed.topic_embedding = new_embedding
                feed.save()

            logging.info(
                f"Recrawled topics and recalculated embedding for feed: {feed.name}"
            )
        else:
            logging.warning(f"No topics found for feed: {feed.name}")

    except Feed.DoesNotExist:
        logging.error(f"Feed with id {feed_id} does not exist")
    except Exception as e:
        logging.error(
            f"Error recrawling topics and recalculating embedding for feed {feed_id}: {str(e)}"
        )


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
