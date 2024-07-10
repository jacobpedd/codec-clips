from django.core.management.base import BaseCommand
from web.tasks import re_rank_using_views_for_user


class Command(BaseCommand):
    help = "Re-rank clips for a specific user"

    def add_arguments(self, parser):
        parser.add_argument(
            "user_id", type=int, help="The ID of the user to rank clips for"
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        re_rank_using_views_for_user.delay(user_id)
