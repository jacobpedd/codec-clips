from django.core.management.base import BaseCommand
from fastembed import TextEmbedding
from web.lib.r2 import get_audio_transcript
from web.models import Clip, Feed, FeedTopic
from django.db.models import Prefetch
from memory_profiler import profile
import psutil
import os


class Command(BaseCommand):
    help = "Test if we can embed without running out of memory"

    @profile
    def handle(self, *args, **options):
        print("Getting topic strings...")
        self.print_memory_usage("Initial")

        embedding_model = TextEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5-Q")
        self.print_memory_usage("After initializing embedding model")

        # Get all feeds and prefetch their topics
        clips = Clip.objects.all().order_by("-created_at")[:100]
        for clip in clips:
            print(f"Found clip: {clip.name} ({clip.id})")
            self.print_memory_usage("After fetching clip")

            # Get the clip transcript
            transcript = get_audio_transcript(clip.feed_item.transcript_bucket_key)
            clip_transcript = ""
            for utterance in transcript:
                if (
                    utterance["start"] > clip.start_time
                    and utterance["end"] < clip.end_time
                ):
                    clip_transcript += f"{utterance['speaker']}\n"
                    clip_transcript += f"{utterance['text']}\n"
            print(f"Clip transcript length: {len(clip_transcript)}")
            self.print_memory_usage("After fetching transcript")

            embeddings_generator = embedding_model.embed(
                [clip_transcript],
            )
            self.print_memory_usage("After creating embeddings generator")

            embeddings_list = list(embeddings_generator)
            self.print_memory_usage("After converting embeddings to list")

            print(f"Embedded {len(embeddings_list)} topics")
            self.print_memory_usage("Final")

    def print_memory_usage(self, step):
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        print(f"Memory usage at {step}: {memory_info.rss / 1024 / 1024:.2f} MB")
