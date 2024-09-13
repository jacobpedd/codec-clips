from langsmith import traceable

from web.models import FeedItem

from .transcript_utils import format_clip_prompt
from .critique_clip import critique_clip
from .generate_clips import generate_clips
from .add_metadata import add_metadata


@traceable
def clipper(
    transcript: list, feed_item: FeedItem, max_iters: int = 5, max_retries: int = 1
):
    # Generate clips with retries
    for attempt in range(max_retries):
        try:
            clips, iters = generate_clips(transcript, max_iters=max_iters)
            break
        except:
            clips = []
            iters = -1
            continue

    # Refine clips
    # clips = [refine_clip(transcript, clip) for clip in clips]
    clip_len = len(clips)
    clips = filter_overlapping_clips(clips)
    if len(clips) < clip_len:
        print(f"Filtered {clip_len - len(clips)} clips due to overlap after refinement")

    # Add metadata
    clips = [add_metadata(transcript, clip, feed_item) for clip in clips]

    return clips, iters, attempt


def refine_clip(transcript: str, clip: dict) -> tuple:
    clip_prompt, sentence_timings = format_clip_prompt(transcript, clip)
    clip = critique_clip(clip_prompt, clip)
    # Calculate new timings
    clip["start"] = sentence_timings[clip["start_index"]]["start"]
    clip["end"] = sentence_timings[clip["end_index"]]["end"]
    return clip


def filter_overlapping_clips(clips):
    if not clips:
        return []

    filtered_clips = [clips[0]]

    for current_clip in clips[1:]:
        last_clip = filtered_clips[-1]

        # Check for overlap
        if current_clip["start"] >= last_clip["end"]:
            # No overlap, add the clip
            filtered_clips.append(current_clip)
        # If there's an overlap, we simply don't add the current clip

    return filtered_clips
