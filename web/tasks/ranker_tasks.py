from django.db import transaction
from django.db.models import F, Window, FloatField
from django.db.models.functions import PercentRank
from django.core.paginator import Paginator
from celery import shared_task
from web.models import Feed
import time


@shared_task
def rank_all_feeds_popularity() -> None:
    start_time = time.time()
    batch_size = 1000

    # Get total number of feeds
    total_feeds = Feed.objects.count()
    print(f"Total feeds: {total_feeds}")

    # Use Django's Paginator for efficient batching
    paginator = Paginator(Feed.objects.all().order_by("id"), batch_size)

    for page_number in paginator.page_range:
        with transaction.atomic():
            # Get the current page of feeds
            page = paginator.page(page_number)

            # Calculate percentile ranks for the batch
            feed_batch = Feed.objects.filter(id__in=page.object_list).annotate(
                percentile_rank=Window(
                    expression=PercentRank(),
                    order_by=F("total_itunes_ratings").asc(),
                    partition_by=F("id"),  # Ensure correct partitioning
                    output_field=FloatField(),
                )
            )

            # Prepare bulk update
            feeds_to_update = [
                Feed(id=feed.id, popularity_percentile=feed.percentile_rank)
                for feed in feed_batch
            ]

            # Perform bulk update
            Feed.objects.bulk_update(feeds_to_update, ["popularity_percentile"])

        print(f"Processed feeds {page.start_index()} to {page.end_index()}")

    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
    print("Successfully updated percentile ranks for all Feed instances")
