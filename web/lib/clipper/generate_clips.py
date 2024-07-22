import json
from braintrust import init_logger, traced

from .suggest_moments import suggest_moments
from .suggest_clip import suggest_clip
from .critique_clip import critique_clip
from .transcript_utils import find_phrase
from .add_metadata import add_metadata


logger = init_logger(project="Clipper")


@traced
def generate_clips(transcript, max_clips=5):
    moments = suggest_moments(transcript)
    moments = moments[:max_clips]
    clips = [generate_clip_for_moment(transcript, moment) for moment in moments]
    clips = [clip for clip in clips if clip is not None]
    if len(clips) < 0:
        raise ValueError("No clips passed the critique")
    clips = [add_metadata(transcript, clip) for clip in clips]
    return clips


def generate_clip_for_moment(transcript: list, moment: [dict]):
    print(f"Generating clip for moment:\n{json.dumps(moment, indent=2)}")

    # Editing variables
    feedback = None
    clip = None

    # Editing loop
    max_edits = 3
    edits = 0
    while True:
        clip = suggest_clip(transcript, moment, clip, feedback)
        print(f"\n\nSuggested clip:\n{json.dumps(clip, indent=2)}")
        feedback = critique_clip(transcript, moment, clip)
        if feedback is None:
            print("Critique model approved the clip")
            break
        else:
            print(f"\n\nFeedback:\n{feedback}")

        edits += 1
        if edits >= max_edits:
            print(f"Maximum number of edits reached: {max_edits}")
            return None

    # Add start and end timings to the clip
    clip["quote"] = moment["quote"]
    clip["start"] = find_phrase(transcript, clip["start_quote"])["start"]
    clip["end"] = find_phrase(transcript, clip["end_quote"])["end"]
    return clip
