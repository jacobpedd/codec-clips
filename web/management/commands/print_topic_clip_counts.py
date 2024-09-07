from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from web.models import Topic, ClipTopicScore


class Command(BaseCommand):
    help = "Prints the number of primary and non-primary clips assigned to each topic, in descending order of total clips"

    def handle(self, *args, **options):
        topics = Topic.objects.annotate(
            primary_clips=Count(
                "cliptopicscore", filter=Q(cliptopicscore__is_primary=True)
            ),
            non_primary_clips=Count(
                "cliptopicscore", filter=Q(cliptopicscore__is_primary=False)
            ),
            total_clips=Count("cliptopicscore"),
        ).order_by("-total_clips")

        self.stdout.write(
            self.style.SUCCESS("Topic Clip Counts (ordered by total clips):")
        )
        self.stdout.write("=" * 80)
        self.stdout.write(
            f"{'Topic Name':<40}{'Primary':<10}{'Non-Primary':<15}{'Total':<10}"
        )
        self.stdout.write("-" * 80)

        for topic in topics:
            self.stdout.write(
                f"{topic.name[:39]:<40}{topic.primary_clips:<10}{topic.non_primary_clips:<15}{topic.total_clips:<10}"
            )

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("End of report"))
