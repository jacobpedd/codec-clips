import numpy as np
from celery import shared_task
from cohere import Client
from django.db import transaction
from codec import settings
from web.models import Feed
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
