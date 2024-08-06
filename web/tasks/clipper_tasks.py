import os
import ffmpeg
import soundfile as sf
import pyloudnorm as pyln
from celery import shared_task
from celery.utils.log import get_task_logger
from web.lib.clipper import clipper, generate_clips_audio
from web.lib.clipper.transcript_utils import format_transcript_by_time
from web.lib.embed import get_embedding
from web.lib.r2 import get_audio_transcript, download_audio_file, upload_file_to_r2
from web.models import FeedItem, Clip

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

    # Generate clip embeddings
    clip_transcript = format_transcript_by_time(
        transcript, clips[0]["start"], clips[0]["end"]
    )
    clip_embedding = get_embedding(clip_transcript)

    # Save clips to models and normalize audio
    for clip, clip_audio_bucket_key in zip(clips, clip_audio_bucket_keys):
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
    try:
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
    except Exception as e:
        return f"Error updating embedding for clip {clip_id}: {str(e)}"
