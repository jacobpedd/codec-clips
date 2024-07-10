from django.core.management.base import BaseCommand
from web.tasks import rank_new_clips_for_user


class Command(BaseCommand):
    help = "Rank new clips for a specific user"

    def add_arguments(self, parser):
        parser.add_argument(
            "user_id", type=int, help="The ID of the user to rank clips for"
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        rank_new_clips_for_user.delay(user_id)
