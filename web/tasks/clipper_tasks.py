import os
import ffmpeg
import soundfile as sf
import pyloudnorm as pyln
from celery import shared_task
from celery.utils.log import get_task_logger
from web.lib.categorize import get_categories
from web.lib.clipper import clipper, generate_clips_audio
from web.lib.clipper.transcript_utils import format_transcript_by_time
from web.lib.embed import get_embedding
from web.lib.r2 import get_audio_transcript, download_audio_file, upload_file_to_r2
from web.models import Category, ClipCategoryScore, FeedItem, Clip

logging = get_task_logger(__name__)

TARGET_LUFS = -16  # Apple recommended loudness for podcasts


# NOTE: This function is triggered from signals.py when a new feed item is created
@shared_task(rate_limit="10/m")
def generate_clips_from_feed_item(feed_item_id: int) -> None:
    feed_item = FeedItem.objects.get(id=feed_item_id)

    # Generate clips with LLM
    transcript = get_audio_transcript(feed_item.transcript_bucket_key)
    clips, _, _ = clipper(transcript)

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

        # Get categories for the clip
        categories = get_categories(clip_transcript)
        # Reverse so high scores overwrite low scores
        categories.reverse()
        for category in categories:
            update_category_and_parents(new_clip, category.name, category.confidence)

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


@shared_task(rate_limit="600/m")
def update_clip_categories(clip_id: int) -> None:
    clip = Clip.objects.get(id=clip_id)

    # Get the transcript
    transcript = get_audio_transcript(clip.feed_item.transcript_bucket_key)

    # Format the transcript for the specific clip
    clip_transcript = format_transcript_by_time(
        transcript, clip.start_time, clip.end_time
    )

    categories = get_categories(clip_transcript)

    # Reverse so high scores overwrite low scores
    categories.reverse()

    for category in categories:
        update_category_and_parents(clip, category.name, category.confidence)

    return f"Successfully updated categories for clip {clip_id}"


def update_category_and_parents(clip, full_path, score):
    if full_path is None or full_path == "":
        return None

    parts = full_path.rsplit("/", 1)

    # Handle the case where there's no parent path
    if len(parts) > 1:  # This means there's no "/" in the full_path
        parent_path = parts[0]
        update_category_and_parents(clip, parent_path, score)

    category = Category.objects.filter(name=full_path).first()
    if not category:
        raise ValueError(f"Category {full_path} does not exist")

    # Update the ClipCategoryScore for this clip and category
    ClipCategoryScore.objects.update_or_create(
        clip=clip, category=category, defaults={"score": score}
    )
