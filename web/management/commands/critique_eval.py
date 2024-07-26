import os
import json
import hashlib
import shutil
from django.core.management.base import BaseCommand
from web.lib.clipper import critique_clip
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run
from web.lib.clipper.clip_audio import save_clip_audio
from web.lib.clipper.transcript_utils import (
    format_clip_prompt,
)

from web.lib.r2 import download_audio_file, get_audio_transcript

DATA_DIR = "./data"


class Command(BaseCommand):
    help = "Run clipper eval on a langchain dataset"

    def add_arguments(self, parser):
        parser.add_argument(
            "--description",
            type=str,
            default="Baseline",
            help="Description of the experiment",
        )
        parser.add_argument(
            "--save_audio",
            action="store_true",
            help="Whether to download clips audio files",
        )

    def handle(self, *args, **options):
        description = options["description"]
        audio = options["save_audio"]

        evaluate(
            lambda inputs: run_critique(inputs, audio),
            data="critique-eval",
            evaluators=[eval_critique],
            experiment_prefix="Critique eval experiment",
            description=description,
            max_concurrency=10,
        )


def run_critique(inputs: dict, audio: bool) -> dict:
    clip = critique_clip(inputs["transcript"], inputs["metadata"])
    return {
        "end_index": clip["end_index"],
        "end_change": clip["end_index"] != inputs["metadata"]["end_index"],
        "start_index": clip["start_index"],
        "start_change": clip["start_index"] != inputs["metadata"]["start_index"],
    }


def eval_critique(root_run: Run, example: Example):
    results = [
        {
            "key": "pass",
            "score": root_run.outputs["start_index"] == example.outputs["start_index"]
            and root_run.outputs["end_index"] == example.outputs["end_index"],
        },
        {
            "key": "start_diff",
            "score": abs(
                root_run.outputs["start_index"] - example.outputs["start_index"]
            ),
        },
        {
            "key": "end_diff",
            "score": abs(root_run.outputs["end_index"] - example.outputs["end_index"]),
        },
        {
            "key": "start_change",
            "score": example.inputs["metadata"]["start_change"]
            == root_run.outputs["start_change"],
        },
        {
            "key": "end_change",
            "score": example.inputs["metadata"]["end_change"]
            == root_run.outputs["end_change"],
        },
    ]

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
        print(f"Saving clip: {clip['name']}")
        if not os.path.exists(clip_dir):
            os.makedirs(clip_dir)

        # Save the clip transcript markdown
        clip_transcript, _ = format_clip_prompt(transcript, clip)
        with open(f"{clip_dir}/transcript.md", "w") as f:
            f.write(clip_transcript)

        # Save the clip metadata
        with open(f"{clip_dir}/metadata.json", "w") as f:
            f.write(json.dumps(clip, indent=2))

        # Save the clip audio
        save_clip_audio(clip_dir, audio_file_path, clip)
        output_filename = f"clip_{clip['name'].replace(' ', '_')}.mp3"
        os.rename(f"{clip_dir}/{output_filename}", f"{clip_dir}/audio.mp3")
