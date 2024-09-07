from django.core.management.base import BaseCommand
from web.models import Clip, Category, ClipCategoryScore
from django.db.models import Max
import random
from web.lib.clip_tagger.assign_categories import assign_categories


class Command(BaseCommand):
    help = "Generate and save categories for a specific clip or a random clip"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clip_id", type=int, help="ID of the clip to categorize (optional)"
        )

    def handle(self, *args, **options):
        clip_id = options.get("clip_id")

        if clip_id:
            try:
                clip = Clip.objects.get(id=clip_id)
            except Clip.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Clip with ID {clip_id} does not exist")
                )
                return
        else:
            # Get a random clip
            max_id = Clip.objects.all().aggregate(max_id=Max("id"))["max_id"]
            while True:
                pk = random.randint(1, max_id)
                clip = Clip.objects.filter(pk=pk).first()
                if clip:
                    break

        self.stdout.write(
            self.style.SUCCESS(f"Finding categories for clip: {clip.name}")
        )

        # Fetch all categories from the database
        categories = Category.objects.all()

        # Assign categories to the clip
        explanation, assigned_categories = assign_categories(clip, categories)

        self.stdout.write(self.style.SUCCESS("Category Assignment:"))
        self.stdout.write(f"Explanation: {explanation}")

        # Print and save assigned categories
        for category in assigned_categories:
            if category.parent:
                self.stdout.write(self.style.SUCCESS(f"  ◦ {category.name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"• {category.name}"))

            # Save the category assignment to the database
            # ClipCategoryScore.objects.update_or_create(
            #     clip=clip,
            #     category=category,
            #     defaults={"score": 1.0},  # You might want to adjust this score
            # )

        # self.stdout.write(self.style.SUCCESS("Categories saved to database."))
