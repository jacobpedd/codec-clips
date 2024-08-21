from django.core.management.base import BaseCommand
from web.models import Category


class Command(BaseCommand):
    help = "Load categories from a text file into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="The path to the text file containing the categories",
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs["file_path"]

        try:
            # Delete all existing categories
            Category.objects.all().delete()

            with open(file_path, "r") as file:
                categories = file.readlines()

            for line in categories:
                line = line.strip()
                if line:
                    self.create_category_hierarchy(line)

            self.stdout.write(self.style.SUCCESS("Successfully loaded categories"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))

    def create_category_hierarchy(self, full_path):
        if full_path is None or full_path == "":
            return None

        parts = full_path.rsplit("/", 1)

        # Handle the case where there's no parent path
        if len(parts) == 1:  # This means there's no "/" in the full_path
            parent = None
        else:
            parent_path = parts[0]
            parent = self.create_category_hierarchy(parent_path)

        category, created = Category.objects.get_or_create(
            name=full_path, parent=parent
        )

        return category
