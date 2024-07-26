import os
import ffmpeg

from web.lib.r2 import download_audio_file, upload_file_to_r2


def save_clip_audio(output_dir, audio_file_path: str, clip: dict):
    output_filename = f"clip_{clip['name'].replace(' ', '_')}.mp3"
    output_path = os.path.join(output_dir, output_filename)

    # Convert milliseconds to seconds
    start_seconds = clip["start"] / 1000.0
    duration_seconds = (clip["end"] - clip["start"]) / 1000.0

    # Use ffmpeg to create the clip
    (
        ffmpeg.input(audio_file_path, ss=start_seconds, t=duration_seconds)
        .output(output_path, acodec="libmp3lame", ab="128k")
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )

    return output_path


def generate_clips_audio(audio_bucket_key: str, clips: list[dict]):
    # Download the audio file from R2 to the disk
    audio_file_path = download_audio_file(audio_bucket_key)
    print(f"Downloaded audio file to {audio_file_path}")

    clip_bucket_keys = []
    try:
        for clip in clips:
            clip_file_path = None
            try:
                # Use ffmpeg to create the clip
                clip_file_path = save_clip_audio("/tmp/", audio_file_path, clip)

                # Upload the clip to R2
                clip_key = f"clip-{os.path.basename(audio_bucket_key)}-{clip_file_path}"
                upload_file_to_r2(clip_file_path, clip_key)
                print(f"Uploaded clip to R2: {clip_key}")

                clip_bucket_keys.append(clip_key)
            except Exception as e:
                raise e
            finally:
                # Clean up the temporary clip file
                if clip_file_path is not None and os.path.exists(clip_file_path):
                    os.remove(clip_file_path)
                    print(f"Cleaned up temporary clip file: {clip_file_path}")
    except Exception as e:
        raise e
    finally:
        # Clean up the temporary input audio file
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            print(f"Cleaned up temporary audio file: {audio_file_path}")

    return clip_bucket_keys
