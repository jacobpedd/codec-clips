from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery, Exists, F, Case, When, FloatField, Avg
from django.contrib.auth.models import User
from web.models import Feed, FeedItem, Clip, FeedUserInterest
from web.tasks import crawl_feed, generate_clips_from_feed_item
from pgvector.django import CosineDistance


class Command(BaseCommand):
    help = "Check top feeds for new items and generate clips if needed"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clip",
            action="store_true",
            help="Whether to fetch items or clip",
        )

    def handle(self, *args, **options):
        clip = options["clip"]
        self.stdout.write("Starting to process top feeds...")

        # Get top 500 feeds by iTunes ratings
        top_feeds = Feed.objects.filter(is_english=True).order_by(
            "-total_itunes_ratings"
        )[:500]

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
            user_feed_scores = (
                Feed.objects.filter(is_english=True)
                .exclude(id__in=top_feeds)  # Exclude feeds already in top feeds
                .annotate(
                    similarity=CosineDistance("topic_embedding", avg_embedding),
                    score=Case(
                        When(
                            similarity__isnull=False,
                            then=(1 - F("similarity")) * 0.8
                            + F("popularity_percentile") * 0.2,
                        ),
                        default=F("popularity_percentile"),
                        output_field=FloatField(),
                    ),
                )
                .order_by("-score")[:100]
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
        sorted_feed_scores = sorted(
            avg_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Take the top 500 scored feeds for the user base
        top_user_feeds = [feed_id for feed_id, _ in sorted_feed_scores[:500]]

        # Combine top_feeds and top_user_feeds
        feeds = list(set(top_feeds.values_list("id", flat=True)) | set(top_user_feeds))

        # Create a subquery to get the latest feed item for each feed
        latest_item = (
            FeedItem.objects.filter(feed=OuterRef("pk"))
            .order_by("-posted_at")
            .values("id")[:1]
        )

        # Annotate feeds with their latest item and whether it has clips
        feeds_to_process = Feed.objects.filter(id__in=feeds).annotate(
            latest_item_id=Subquery(latest_item),
            has_clips=Exists(
                Clip.objects.filter(feed_item_id=OuterRef("latest_item_id"))
            ),
        )

        # Process each feed
        for feed in feeds_to_process:
            self.stdout.write(f"Processing feed: {feed.name}")
            if clip:
                # If the latest item doesn't have clips, generate them
                if feed.latest_item_id and not feed.has_clips:
                    self.stdout.write(
                        f"Generating clips for latest item in feed: {feed.name}"
                    )
                    generate_clips_from_feed_item.delay(feed.latest_item_id)
            else:
                # Check for new feed items
                crawl_feed.delay(feed.id)

        self.stdout.write(self.style.SUCCESS("Finished processing all feeds"))
