import os
import json
import hashlib
import shutil
from django.core.management.base import BaseCommand
from web.lib.clipper import clipper
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run
from web.lib.clipper.clip_audio import save_clip_audio
from web.lib.clipper.transcript_utils import (
    format_clip_prompt,
)
from web.lib.r2 import download_audio_file, get_audio_transcript
from web.models import FeedItem
from web.lib.clipper.transcript_utils import format_episode_description

DATA_DIR = "./data"


class Command(BaseCommand):
    help = "Run clipper eval on a langchain dataset"

    def add_arguments(self, parser):
        parser.add_argument(
            "--name", type=str, required=True, help="Name of the dataset"
        )
        parser.add_argument(
            "--description",
            type=str,
            default="Baseline",
            help="Description of the experiment",
        )
        parser.add_argument(
            "--max_iters",
            type=int,
            default=6,
            help="Maximum number of iterations for the evaluation",
        )
        parser.add_argument(
            "--max_retries",
            type=int,
            default=2,
            help="Maximum number of retries for clipper",
        )
        parser.add_argument(
            "--save_audio",
            action="store_true",
            help="Whether to download clips audio files",
        )

    def handle(self, *args, **options):
        dataset_name = options["name"]
        description = options["description"]
        max_iters = options["max_iters"]
        max_retries = options["max_retries"]
        audio = options["save_audio"]

        evaluate(
            lambda inputs: run_clipper(inputs, max_iters, max_retries, audio),
            data=dataset_name,
            evaluators=[eval_clipper],
            experiment_prefix="Clipper eval " + dataset_name,
            description=description,
            max_concurrency=10,
        )


def run_clipper(inputs: dict, max_iters: int, max_retries: int, audio: bool) -> dict:
    feed_item = FeedItem.objects.get(id=inputs["id"])

    clips, iters, retries = clipper(
        inputs["transcript"], feed_item, max_iters=max_iters, max_retries=max_retries
    )

    if audio:
        save_clip_data(inputs["name"], inputs["audio_url"], clips)
    return {"output": {"clips": clips, "iters": iters, "retries": retries}}


def eval_clipper(root_run: Run, example: Example):
    output = root_run.outputs.get("output")
    results = []

    if output is not None and len(output["clips"]) > 0:
        results.append({"key": "clip_count", "score": len(output["clips"])})
        results.append({"key": "iters", "score": output["iters"]})
        results.append({"key": "pass", "score": True})
        results.append({"key": "retries", "score": output["retries"]})
    else:
        results.append({"key": "pass", "score": False})

    return {
        "results": results,
    }


def save_clip_data(name, audio_url: str, clips: list):
    # Check if data directory exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Check if item directory exists
    item_dir = os.path.join(DATA_DIR, name)
    if not os.path.exists(item_dir):
        os.makedirs(item_dir)

    # Download the audio file from R2
    audio_file_path = f"{item_dir}/audio.mp3"
    url_hash = hashlib.md5(audio_url.encode()).hexdigest()
    audio_bucket_key = f"audio-{url_hash}"
    if not os.path.exists(audio_file_path):
        download_audio_file(audio_bucket_key, item_dir)
        os.rename(f"{item_dir}/{audio_bucket_key}", audio_file_path)

    # Download the transcript from R2
    transcript_file_path = f"{item_dir}/transcript.json"
    transcript_bucket_key = f"transcript-{url_hash}"
    if not os.path.exists(transcript_file_path):
        transcript = get_audio_transcript(transcript_bucket_key)
        with open(transcript_file_path, "w") as f:
            f.write(json.dumps(transcript, indent=2))
    else:
        with open(transcript_file_path, "r") as f:
            transcript = json.load(f)

    # Delete clips dir if it exists
    clips_dir = f"{item_dir}/clips"
    if os.path.exists(clips_dir):
        shutil.rmtree(clips_dir)
        os.mkdir(clips_dir)
    else:
        os.mkdir(clips_dir)

    # Save clips
    for clip in clips:
        clip_dir = f"{clips_dir}/{clip['name']}"
        print(f"Saving clip: {clip['name']} {clip['start_index']}:{clip['end_index']}")
        if not os.path.exists(clip_dir):
            os.makedirs(clip_dir)

        # Save the clip transcript markdown
        clip_transcript, _ = format_clip_prompt(transcript, clip)
        # Only save the text between <CLIP> and </CLIP>
        with open(f"{clip_dir}/transcript.md", "w") as f:
            f.write(clip_transcript)

        # Save the clip metadata
        with open(f"{clip_dir}/metadata.json", "w") as f:
            f.write(json.dumps(clip, indent=2))

        # Save the clip audio
        save_clip_audio(clip_dir, audio_file_path, clip)
        output_filename = f"clip_{clip['name'].replace(' ', '_')}.mp3"
        os.rename(f"{clip_dir}/{output_filename}", f"{clip_dir}/audio.mp3")
