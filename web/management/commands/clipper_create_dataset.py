from django.core.management.base import BaseCommand
from django.conf import settings
from web.models import FeedItem
from langsmith import Client
from web.lib.r2 import get_audio_transcript


class Command(BaseCommand):
    help = "Create a LangChain dataset from the most recent FeedItems"

    def add_arguments(self, parser):
        parser.add_argument(
            "--size",
            type=int,
            default=100,
            help="Number of FeedItems to include in the dataset",
        )
        parser.add_argument(
            "--name", type=str, required=True, help="Name of the dataset"
        )

    def handle(self, *args, **options):
        dataset_size = options["size"]
        dataset_name = options["name"]

        # Initialize LangSmith client
        client = Client(api_key=settings.LANGSMITH_API_KEY)

        # Check if the dataset already exists
        dataset = None
        datasets = client.list_datasets(dataset_name=dataset_name)
        for dataset in datasets:
            if dataset.name == dataset_name:
                print(f"Dataset {dataset_name} already exists")
                dataset = dataset
                break
        if dataset is None:
            # Create the dataset
            print(f"Creating dataset {dataset_name}")
            dataset = client.create_dataset(
                dataset_name=dataset_name,
                description=f"Clipper input (transcripts) from the {dataset_size} most recent FeedItems",
            )

        # Loop through existing examples
        existing_examples = client.list_examples(dataset_id=dataset.id)
        for example in existing_examples:
            client.delete_example(example_id=example.id)

        # Fetch the most recent FeedItems
        feed_items = FeedItem.objects.order_by("-created_at")[:dataset_size]

        for item in feed_items:
            self.stdout.write(f"Processing FeedItem: {item.name}")

            # Get the transcript from R2
            transcript = get_audio_transcript(item.transcript_bucket_key)

            if transcript is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Failed to retrieve transcript for FeedItem: {item.name}"
                    )
                )
                continue

            # Create an example in the dataset
            client.create_example(
                inputs={
                    "transcript": transcript,
                    "audio_url": item.audio_url,
                    "name": f"[{item.feed.name}] {item.name}",
                    "id": item.id,
                },
                outputs=None,
                dataset_id=dataset.id,
                metadata={
                    "feed_item_id": item.id,
                    "feed_item_name": item.name,
                    "feed_item_audio_url": item.audio_url,
                    "feed_name": item.feed.name,
                    "duration": item.duration,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created dataset "{dataset_name}" with {dataset_size} examples'
            )
        )
