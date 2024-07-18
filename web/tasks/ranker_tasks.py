from datetime import datetime, timedelta
from celery import chain, group, shared_task
from cohere import Client
from django.utils import timezone
from django.db import transaction
from django.db.models import Exists, OuterRef
import numpy as np
from codec import settings
from web.lib.ranker import clip_to_text, get_user_clip_examples
from web.models import Clip, ClipUserScore, ClipUserView, Feed
from django.contrib.auth.models import User
from celery.utils.log import get_task_logger

logging = get_task_logger(__name__)

co = Client(settings.COHERE_API_KEY)


@shared_task
def rank_all_feeds_popularity() -> None:
    # TODO: This should probably check to see if it needs to be recalculated
    # Retrieve all total_itunes_ratings values and corresponding Feed instances
    all_feeds = Feed.objects.all()
    all_ratings = np.array([feed.total_itunes_ratings for feed in all_feeds])

    # Calculate ranks
    sorted_indices = np.argsort(all_ratings)
    ranks = np.empty_like(sorted_indices)
    ranks[sorted_indices] = np.arange(len(all_ratings))

    # Calculate percentile ranks
    percentile_ranks = (ranks + 1) / len(all_ratings)

    # Update each Feed instance with its percentile rank
    with transaction.atomic():
        for feed, percentile_rank in zip(all_feeds, percentile_ranks):
            feed.popularity_percentile = percentile_rank
            feed.save(update_fields=["popularity_percentile"])

    print("Successfully updated percentile ranks for all Feed instances")


@shared_task(priority=0)
def re_rank_using_views() -> None:
    # Get all user_ids
    user_ids = User.objects.all().values_list("id", flat=True)

    # Create a group of tasks for processing each feed
    tasks = group(re_rank_using_views_for_user.s(user_id) for user_id in user_ids)

    # Execute the group of tasks without waiting
    result = tasks.apply_async()

    # Log the group result ID for potential later use
    group_result_id = result.id

    logging.info(
        f"Started processing {len(user_ids)} users. Group result ID: {group_result_id}"
    )


@shared_task(priority=0)
def re_rank_using_views_for_user(user_id: int) -> None:
    # Check how many unprocessed ClipUserViews for user
    unprocessed_count = ClipUserView.objects.filter(
        user_id=user_id, processed=False
    ).count()

    # If there are less than 10 unprocessed ClipUserViews, wait until there are more
    if unprocessed_count < 10:
        logging.info(f"Not enough unprocessed ClipUserViews for user {user_id}")
        return

    # One batch of high scored clips to use as examples
    # Get ClipUserScores less than 1 week old ordered by highest score
    one_week_ago = datetime.now() - timedelta(days=7)
    top_scores = ClipUserScore.objects.filter(
        user_id=user_id, created_at__gte=one_week_ago, score__isnull=False
    ).order_by("-score")[:96]
    top_clip_ids = [score.clip_id for score in top_scores]

    # One batch of random clips to use as examples
    # Get random clips less than 1 week old that are scored
    random_scores = ClipUserScore.objects.filter(user_id=user_id).order_by("?")[:96]
    random_clip_ids = [score.clip_id for score in random_scores]

    # Chain the ranking tasks with a final task to mark views as processed
    chain(
        group(
            rank_clips_for_user.s(user_id, top_clip_ids),
            rank_clips_for_user.s(user_id, random_clip_ids),
        ),
        complete_re_rank_for_user.s(user_id),
    ).apply_async()

    logging.info(f"Started re-ranking process for user {user_id}")


@shared_task(priority=0)
def complete_re_rank_for_user(results, user_id: int):
    # 'results' parameter will contain the results from the previous tasks in the chain
    # We don't need to use it, but it needs to be there to accept the passed results
    updated = ClipUserView.objects.filter(user_id=user_id, processed=False).update(
        processed=True
    )
    logging.info(f"Marked {updated} views as processed for user {user_id}")
    return updated


# Runs on cron every hour
@shared_task
def rank_new_clips() -> None:
    # Get all user_ids
    user_ids = User.objects.all().values_list("id", flat=True)

    # Create a group of tasks for processing each feed
    tasks = group(rank_new_clips_for_user.s(user_id) for user_id in user_ids)

    # Execute the group of tasks without waiting
    result = tasks.apply_async()

    # Log the group result ID for potential later use
    group_result_id = result.id

    logging.info(
        f"Started processing {len(user_ids)} users. Group result ID: {group_result_id}"
    )


@shared_task(priority=0)
def rank_new_clips_for_user(user_id: int) -> None:
    # Get clips less than 1 week old that aren't viewed or ranked for user
    one_week_ago = datetime.now() - timedelta(days=7)
    clips = (
        Clip.objects.filter(created_at__gte=one_week_ago)
        .exclude(
            Exists(ClipUserView.objects.filter(clip=OuterRef("pk"), user_id=user_id))
        )
        .exclude(
            Exists(ClipUserScore.objects.filter(clip=OuterRef("pk"), user_id=user_id))
        )
        .order_by("-created_at")[:1000]
    )
    clip_ids = [clip.id for clip in clips]

    # Rank in batches of 96 clips
    batch_size = 96
    tasks = []
    for i in range(0, len(clip_ids), batch_size):
        batch = clip_ids[i : i + batch_size]
        tasks.append(rank_clips_for_user.s(user_id, batch))

    if tasks:
        # Execute the group of tasks without waiting
        result = group(tasks).apply_async()

        # Log the group result ID for potential later use
        group_result_id = result.id

        logging.info(
            f"Started processing {len(clip_ids)} clips for user {user_id}. Group result ID: {group_result_id}"
        )
    else:
        logging.info(f"No new clips to rank for user {user_id}")


@shared_task(rate_limit="10000/m", priority=0)
def rank_clips_for_user(user_id: int, clip_ids: [int]) -> None:
    if len(clip_ids) == 0:
        return

    # 96 is the input limit for cohere's classify endpoint
    if len(clip_ids) > 96:
        raise ValueError("Too many clips to rank")

    # Get examples for user
    examples = get_user_clip_examples(user_id)

    # Cohere requires at least 2 examples per label
    complete_count = len([e for e in examples if e.label == "Complete"])
    skipped_count = len([e for e in examples if e.label == "Skipped"])
    if complete_count < 2 or skipped_count < 2:
        # Can't rank clips yet, cold start the user
        logging.info(f"Not enough examples for user {user_id}")
        return

    # Get clips to rank
    clips = Clip.objects.filter(id__in=clip_ids)
    clips_text = [clip_to_text(clip) for clip in clips]

    response = co.classify(
        examples=examples,
        inputs=clips_text,
    )

    # Return list of scores based on the classification
    scores = [
        classification.labels["Complete"].confidence
        for classification in response.classifications
    ]

    # Prepare data for bulk upsert
    clip_user_scores = []
    for clip_id, score in zip(clip_ids, scores):
        # Reset score from 0 to 1 -> 0 -> 100
        clip_user_scores.append(
            ClipUserScore(
                user_id=user_id,
                clip_id=clip_id,
                score=score,
            )
        )

    # Perform bulk upsert
    results = ClipUserScore.objects.bulk_create(
        clip_user_scores,
        update_conflicts=True,
        update_fields=["score"],
        unique_fields=["user_id", "clip_id"],
    )
    logging.info(f"Ranked {len(results)} clips for user {user_id}")
