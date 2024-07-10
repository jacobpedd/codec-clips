from datetime import datetime, timedelta
from cohere import ClassifyExample, Client
from celery import group, shared_task
from django.db.models import Exists, OuterRef, Prefetch
from web.models import Clip, ClipUserScore, ClipUserView
from codec import settings
from django.contrib.auth.models import User
from celery.utils.log import get_task_logger

logging = get_task_logger(__name__)

co = Client(settings.COHERE_API_KEY)


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


@shared_task
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


@shared_task(rate_limit="10000/m")
def rank_clips_for_user(user_id: int, clip_ids: [int]) -> None:
    if len(clip_ids) == 0:
        return

    # 96 is the input limit for cohere's classify endpoint
    if len(clip_ids) > 96:
        raise ValueError("Too many clips to rank")

    # Get examples for user
    examples = get_user_rank_examples(user_id)

    # Cohere requires at least 2 examples per label
    complete_count = len([e for e in examples if e.label == "Complete"])
    skipped_count = len([e for e in examples if e.label == "Skipped"])
    if complete_count < 2 or skipped_count < 2:
        # Can't rank clips yet, cold start the user
        return

    # Get clips to rank
    clips = Clip.objects.filter(id__in=clip_ids)
    inputs = [
        {
            "text": clip_to_text(clip),
            "name": clip.name,
            "id": clip.id,
        }
        for clip in clips
    ]

    response = co.classify(
        examples=examples,
        inputs=[input["text"] for input in inputs],
    )

    # Prepare data for bulk upsert
    clip_user_scores = []
    for input, classification in zip(inputs, response.classifications):
        # Reset score from 0 to 1 -> 0 -> 100
        clip_user_scores.append(
            ClipUserScore(
                user_id=user_id,
                clip_id=input["id"],
                score=classification.labels["Complete"].confidence,
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


def get_user_rank_examples(user_id: str) -> [ClassifyExample]:
    # NOTE: 2500 is the example limit for cohere's classify endpoint
    user_views = (
        ClipUserView.objects.filter(user_id=user_id)
        .select_related("clip__feed_item__feed")
        .prefetch_related(Prefetch("clip__topics", to_attr="prefetched_topics"))
        .order_by("-created_at")[:2500]
    )
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
    return "\n".join(
        [
            f"Clip Name: {clip.name}",
            f"Clip Summary: {clip.summary}",
            f"Episode Name: {clip.feed_item.name}",
            f"Episode Description: {clip.feed_item.body[:1000]}",
            f"Podcast Name: {clip.feed_item.feed.name}",
            f"Podcast Description: {clip.feed_item.feed.description[:1000]}",
        ]
    )
