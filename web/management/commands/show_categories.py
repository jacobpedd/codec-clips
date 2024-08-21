from django.core.management.base import BaseCommand
from django.db.models import Count
from web.models import ClipCategoryScore, Category


class Command(BaseCommand):
    help = "Break down the most popular categories in the dataset of clips"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Limit the number of categories displayed",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        # Fetch top-level categories (no parent)
        top_level_categories = Category.objects.filter(parent__isnull=True)

        # Function to recursively gather all child category IDs
        def get_all_child_categories(category):
            child_categories = Category.objects.filter(parent=category)
            all_child_ids = list(child_categories.values_list("id", flat=True))
            for child in child_categories:
                all_child_ids.extend(get_all_child_categories(child))
            return all_child_ids

        # Print top-level categories and their counts
        self.stdout.write(self.style.SUCCESS("Top-Level Categories:"))
        for top_category in top_level_categories:
            # Get all categories (top-level + all descendants)
            category_ids = [top_category.id] + get_all_child_categories(top_category)

            # Count clips that belong to the top-level category or any of its descendants
            total_clips = (
                ClipCategoryScore.objects.filter(
                    category_id__in=category_ids, score__gt=0.3
                )
                .values("category_id")
                .aggregate(total=Count("clip_id"))["total"]
                or 0
            )
            self.stdout.write("\n---------")
            self.stdout.write(f"{top_category.name}: {total_clips} clips")

            # Fetch and display child categories with more than 100 clips
            def print_child_categories(parent_category, indent_level=1):
                child_categories = Category.objects.filter(parent=parent_category)
                for child_category in child_categories:
                    child_category_clips = (
                        ClipCategoryScore.objects.filter(
                            category=child_category, score__gt=0.3
                        )
                        .values("category_id")
                        .annotate(total_clips=Count("clip_id"))
                        .filter(total_clips__gt=10)
                    )
                    for category_data in child_category_clips:
                        indent = "  " * indent_level
                        if child_category.name.endswith("/Other"):
                            continue
                        self.stdout.write(
                            f"{indent}- {child_category.name}: {category_data['total_clips']} clips"
                        )
                        # Recursive call to print child categories of the current child category
                        print_child_categories(child_category, indent_level + 1)

            # Print all child categories recursively
            print_child_categories(top_category)
