import os
import ffmpeg
import soundfile as sf
import pyloudnorm as pyln
from celery import shared_task
from django.db import transaction
from celery.utils.log import get_task_logger
from web.lib.clip_tagger import clip_tagger
from web.lib.clipper import clipper, generate_clips_audio
from web.lib.clipper.transcript_utils import (
    format_transcript_by_time,
)
from web.lib.embed import get_embedding
from web.lib.r2 import get_audio_transcript, download_audio_file, upload_file_to_r2
from web.models import ClipCategoryScore, ClipTopicScore, FeedItem, Clip

logging = get_task_logger(__name__)

TARGET_LUFS = -16  # Apple recommended loudness for podcasts


# NOTE: This function is triggered from signals.py when a new feed item is created
@shared_task(rate_limit="10/m")
def generate_clips_from_feed_item(feed_item_id: int) -> None:
    feed_item = FeedItem.objects.get(id=feed_item_id)

    # Generate clips with LLM
    transcript = get_audio_transcript(feed_item.transcript_bucket_key)
    clips, _, _ = clipper(transcript, feed_item)

    # Create clip audio files
    clip_audio_bucket_keys = generate_clips_audio(feed_item.audio_bucket_key, clips)

    # Save clips to models and normalize audio
    for clip, clip_audio_bucket_key in zip(clips, clip_audio_bucket_keys):
        # Generate clip embeddings
        clip_transcript = format_transcript_by_time(
            transcript, clip["start"], clip["end"]
        )
        clip_embedding = get_embedding(clip_transcript)

        # Create the clip
        new_clip = Clip.objects.create(
            name=clip["name"],
            body="",
            summary=clip["summary"],
            start_time=clip["start"],
            end_time=clip["end"],
            audio_bucket_key=clip_audio_bucket_key,
            transcript_embedding=clip_embedding,
            feed_item=feed_item,
        )

        # Run tagging for the new clip
        run_clip_tagger.delay(new_clip.id)

        # Queue normalization task for the new clip
        normalize_clip_audio.delay(new_clip.id)

    logging.info("[Finished] Generating clips for feed item: %s", feed_item.name)


@shared_task
def normalize_clip_audio(clip_id):
    clip = Clip.objects.get(id=clip_id)

    # Download the clip audio file
    audio_file_path = download_audio_file(clip.audio_bucket_key)

    # Measure initial loudness
    data, rate = sf.read(audio_file_path)
    meter = pyln.Meter(rate)
    initial_loudness = meter.integrated_loudness(data)

    # Calculate the volume adjustment needed
    volume_change = TARGET_LUFS - initial_loudness

    # Normalize the audio using ffmpeg
    output_path = f"{audio_file_path}_normalized.mp3"

    (
        ffmpeg.input(audio_file_path)
        .filter("volume", volume=f"{volume_change}dB")
        .output(output_path, acodec="libmp3lame", ab="128k")
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )

    # Upload the normalized audio to R2, overwriting the original file
    upload_file_to_r2(output_path, clip.audio_bucket_key)

    # Clean up temporary files
    os.remove(audio_file_path)
    os.remove(output_path)

    logging.info(f"Clip {clip_id} normalization results:")
    logging.info(f"  Initial loudness: {initial_loudness:.2f} LUFS")
    logging.info(f"  Target loudness: {TARGET_LUFS:.2f} LUFS")


@shared_task
def update_clip_embedding(clip_id):
    clip = Clip.objects.get(id=clip_id)
    feed_item = clip.feed_item

    # Get the transcript
    transcript = get_audio_transcript(feed_item.transcript_bucket_key)

    # Format the transcript for the specific clip
    clip_transcript = format_transcript_by_time(
        transcript, clip.start_time, clip.end_time
    )

    # Generate the embedding
    clip_embedding = get_embedding(clip_transcript)

    # Update the clip with the new embedding
    clip.transcript_embedding = clip_embedding
    clip.save()

    return f"Successfully updated embedding for clip {clip_id}"


@shared_task()
def run_clip_tagger(clip_id: int, nearest_neighbors: int = 40) -> None:
    try:
        clip = Clip.objects.get(id=clip_id)
    except Clip.DoesNotExist:
        logging.error(f"Clip with ID {clip_id} does not exist")
        return f"Error: Clip with ID {clip_id} does not exist"

    try:
        categories, primary_topics, mentioned_topics = clip_tagger(
            clip, nearest_neighbors
        )

        logging.info(f"Clip tagger results for clip {clip_id}:")
        logging.info(f"Categories: {categories}")
        logging.info(f"Primary topics: {primary_topics}")
        logging.info(f"Mentioned topics: {mentioned_topics}")

        with transaction.atomic():
            # Delete existing ClipTopicScores and ClipCategoriesScores for this clip
            ClipTopicScore.objects.filter(clip=clip).delete()
            ClipCategoryScore.objects.filter(clip=clip).delete()

            # Save categories
            for category in categories:
                ClipCategoryScore.objects.update_or_create(
                    clip=clip,
                    category=category,
                    defaults={"score": 1.0},
                )

            # Save primary topics
            for topic, score in primary_topics:
                ClipTopicScore.objects.create(
                    clip=clip, topic=topic, score=score, is_primary=True
                )

            # Save mentioned topics
            for topic, score in mentioned_topics:
                ClipTopicScore.objects.create(
                    clip=clip, topic=topic, score=score, is_primary=False
                )

        logging.info(f"Successfully updated topics for clip {clip_id}")
        return f"Successfully updated topics for clip {clip_id}"

    except Exception as e:
        logging.error(f"Error updating topics for clip {clip_id}: {str(e)}")
        logging.exception("Full traceback:")
        return f"Error updating topics for clip {clip_id}: {str(e)}"
