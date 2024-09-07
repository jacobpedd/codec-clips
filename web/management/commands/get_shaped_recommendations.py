import os
import subprocess
import yaml
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from web.models import Clip
from django.conf import settings

User = get_user_model()

DEFAULT_MODEL = "codec_recsys_dev_v1"
SHAPED_VENV_PATH = os.path.join(settings.BASE_DIR, ".shapedenv")


class Command(BaseCommand):
    help = "Get clip recommendations for a user using a specified Shaped model"

    def add_arguments(self, parser):
        parser.add_argument(
            "user_id", type=int, help="ID of the user to get recommendations for"
        )
        parser.add_argument(
            "model_name",
            type=str,
            nargs="?",
            default=DEFAULT_MODEL,
            help=f"Name of the Shaped model to use (default: {DEFAULT_MODEL})",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of recommendations to retrieve (default: 5)",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        model_name = options["model_name"]
        limit = options["limit"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"User with ID {user_id} does not exist")
            )
            return

        # Construct the command to run shaped CLI in the virtual environment
        activate_venv = f"source {SHAPED_VENV_PATH}/bin/activate"
        shaped_command = f"shaped rank --model-name {model_name} --user-id '{user_id}' --limit {limit}"
        full_command = f"{activate_venv} && {shaped_command}"

        # Run the command
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash",
        )

        if result.returncode != 0:
            self.stdout.write(
                self.style.ERROR(f"Error running shaped rank command: {result.stderr}")
            )
            return

        # Parse the YAML output
        try:
            data = yaml.safe_load(result.stdout)
        except yaml.YAMLError as e:
            self.stdout.write(self.style.ERROR(f"Error parsing YAML output: {e}"))
            return

        # Print the recommendations
        self.stdout.write(
            self.style.SUCCESS(
                f"Recommendations for User {user_id} using model {model_name}:"
            )
        )
        self.stdout.write("=" * 100)
        self.stdout.write(f"{'Rank':<5}{'Clip ID':<10}{'Score':<15}{'Clip Name'}")
        self.stdout.write(f"{'':5}{'':10}{'':15}{'Feed Name'}")
        self.stdout.write("-" * 100)

        for rank, (clip_id, score) in enumerate(
            zip(data["ids"], data["scores"]), start=1
        ):
            try:
                clip = Clip.objects.get(id=clip_id)
                clip_name = clip.name
                feed_name = (
                    clip.feed_item.feed.name
                    if clip.feed_item and clip.feed_item.feed
                    else "Unknown Feed"
                )
            except Clip.DoesNotExist:
                clip_name = "Clip not found"
                feed_name = "N/A"

            self.stdout.write(f"{rank:<5}{clip_id:<10}{score:<15.6f}{clip_name}")
            self.stdout.write(f"{'':5}{'':10}{'':15}{feed_name}")
            self.stdout.write("-" * 100)

        self.stdout.write("=" * 100)
