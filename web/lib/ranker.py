from datetime import timedelta
from cohere import ClassifyExample
from django.utils import timezone
import numpy as np
from web.models import Clip, ClipUserView, Feed, FeedUserInterest, FeedUserScore
from celery.utils.log import get_task_logger


logging = get_task_logger(__name__)


# Run when a user follows/blocks a feed in signals.py
def rank_feeds_for_user(user_id: int) -> None:
    # Get feeds the user follows
    followed_feeds = FeedUserInterest.objects.filter(
        user_id=user_id, is_interested=True
    ).select_related("feed")

    if len(followed_feeds) < 3:
        print(f"Not enough followed feeds for user {user_id}")
        return

    # Calculate average embedding of followed feeds
    followed_embeddings = [
        np.array(feed.feed.topic_embedding) for feed in followed_feeds
    ]
    avg_followed_embedding = np.mean(followed_embeddings, axis=0)

    # Get all other English feeds with topics
    input_feeds = (
        Feed.objects.filter(topics__isnull=False, is_english=True)
        .exclude(id__in=[feed.feed.id for feed in followed_feeds])
        .distinct()
    )

    print(f"Found {len(input_feeds)} feeds to rank for user {user_id}")

    # Calculate scores and create FeedUserScore objects
    feed_user_scores = []
    for feed in input_feeds:
        embedding = np.array(feed.topic_embedding)
        score = cosine_similarity(avg_followed_embedding, embedding)
        feed_user_scores.append(
            FeedUserScore(
                user_id=user_id,
                feed_id=feed.id,
                score=score,
            )
        )

    print(f"Ranked {len(feed_user_scores)} feeds for user {user_id}")

    # Bulk create scores
    FeedUserScore.objects.bulk_create(
        feed_user_scores,
        update_conflicts=True,
        update_fields=["score", "updated_at"],
        unique_fields=["user_id", "feed_id"],
    )

    print(
        f"Completed ranking for user {user_id}. Processed {len(feed_user_scores)} feeds."
    )


def get_user_clip_examples(user_id: str) -> [ClassifyExample]:
    # Get base queryset
    base_query = (
        ClipUserView.objects.filter(user_id=user_id)
        .select_related("clip__feed_item__feed")
        .order_by("-created_at")
    )

    # Exclude the most recent view if it's less than 10 min old
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    most_recent_view = base_query.first()
    if most_recent_view and most_recent_view.created_at > ten_minutes_ago:
        logging.info(f"Excluding most recent view because it might be in progress")
        base_query = base_query.exclude(id=most_recent_view.id)

    # Limit to 2500 examples (max for cohere's classify endpoint)
    user_views = base_query[:2500]

    # Create cohere examples for each user view
    examples = []
    for user_view in user_views:
        label = "Complete" if user_view.duration > 90 else "Skipped"
        examples.append(
            ClassifyExample(
                text=clip_to_text(user_view.clip),
                label=label,
            )
        )
    return examples


def clip_to_text(clip: Clip):
    # Returns ~500 tokens per clip, will be truncated at end if needed
    clip_duration = (clip.end_time - clip.start_time) / 1000.0
    clip_minutes = int(clip_duration // 60)
    clip_seconds = int(clip_duration % 60)

    return "\n".join(
        [
            f"Clip Name: {clip.name}",
            f"Clip Summary: {clip.summary}",
            f"Duration: {clip_minutes}m {clip_seconds}s",
            f"Episode Description: {clip.feed_item.body[:1000]}",
            f"Podcast Name: {clip.feed_item.feed.name}",
            f"Podcast Description: {clip.feed_item.feed.description[:1000]}",
        ]
    )


def cosine_similarity(a, b):
    # Ensure the vectors are not zero
    if np.all(a == 0) or np.all(b == 0):
        return 0.0

    # Calculate dot product
    dot_product = np.dot(a, b)

    # Calculate magnitudes
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)

    # Avoid division by zero
    if magnitude_a * magnitude_b == 0:
        return 0.0

    # Calculate cosine similarity
    return dot_product / (magnitude_a * magnitude_b)
