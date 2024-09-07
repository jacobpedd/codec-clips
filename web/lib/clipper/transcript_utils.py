from web.lib.r2 import get_audio_transcript
from web.models import Clip


def format_transcript_prompt(transcript: list):
    format_transcript = ""

    def format_time(ms):
        total_seconds = int(ms / 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    # List of common titles that should not end a sentence
    common_titles = ["mr", "ms", "mrs", "dr", "prof", "rev", "hon", "sr", "jr"]

    sentence_timings = {}
    sentence_index = 0
    for utterance in transcript:
        start_time = format_time(utterance["start"])
        format_transcript += f"# {utterance['speaker']} {start_time}\n"
        last_timestamp = None

        # Process potential sentences to handle special cases
        current_sentence = ""
        word_count = 0
        for i, word in enumerate(utterance["words"]):
            # Initialize sentence timings if the word is at the start of a sentence
            if sentence_index not in sentence_timings:
                sentence_timings[sentence_index] = {"start": word["start"], "end": None}

            if last_timestamp is None:
                last_timestamp = word["start"]

            word_text = word["text"].lower()
            next_word = (
                utterance["words"][i + 1]["text"].lower()
                if i + 1 < len(utterance["words"])
                else ""
            )

            # Check if the word ends with a period and is not a common title
            is_sentence_end = word["text"].endswith((".", "?", "!")) and not (
                word_text.rstrip(".") in common_titles and next_word
            )

            if is_sentence_end:
                current_sentence += word["text"]
                word_count += 1
                # Only end the sentence if it has more than 2 words
                if word_count > 2:
                    format_transcript += f"{sentence_index} {current_sentence}\n"
                    sentence_timings[sentence_index]["end"] = word["end"]
                    current_sentence = ""
                    word_count = 0
                    sentence_index += 1

                    if word["end"] - last_timestamp > 1000 * 60 * 5:
                        # If the sentence is more than 5 min away from last timestamp. add new timestamp
                        format_transcript += (
                            f"# {utterance['speaker']} {format_time(word['end'])}\n"
                        )
                        last_timestamp = word["end"]
                else:
                    # If we added the word without ending the sentence, add a space
                    current_sentence += " "

            else:
                if current_sentence == "":
                    # If the word is at the beginning of a sentence, start a new sentence
                    current_sentence += word["text"] + " "
                else:
                    # We're in the middle of a sentence
                    current_sentence += word["text"] + " "
                word_count += 1

        # End sentence if there's any remaining text
        if current_sentence != "":
            format_transcript += f"{sentence_index} {current_sentence}\n"
            sentence_timings[sentence_index]["end"] = utterance["end"]
            sentence_index += 1

    return format_transcript, sentence_timings


def format_clip_prompt(transcript: list, clip: dict, max_mins=10):
    transcript_prompt, sentence_timings = format_transcript_prompt(transcript)
    # Find which sentence the clip starts and ends at
    clip_start_sentence_index = 0
    for i in range(len(sentence_timings.keys())):
        sentence_timing = sentence_timings[i]
        if sentence_timing["start"] >= clip["start"]:
            clip_start_sentence_index = i
            break
    for i in range(len(sentence_timings.keys())):
        sentence_timing = sentence_timings[i]
        if sentence_timing["end"] >= clip["end"]:
            clip_end_sentence_index = i
            break

    # Find which sentence the max duration starts and ends at
    clip_duration_minutes = (clip["end"] - clip["start"]) / 60000.0
    max_clip_extension_minutes = max_mins - clip_duration_minutes
    max_clip_extension = max_clip_extension_minutes * 60 * 1000
    if max_clip_extension > 0:
        transcript_start_sentence_index = 0
        for i in range(len(sentence_timings.keys())):
            sentence_timing = sentence_timings[i]
            if sentence_timing["start"] >= clip["start"] - max_clip_extension:
                transcript_start_sentence_index = i
                break
        transcript_end_sentence_index = len(sentence_timings.keys()) - 1
        for i in range(len(sentence_timings.keys())):
            sentence_timing = sentence_timings[i]
            if sentence_timing["end"] >= clip["end"] + max_clip_extension:
                transcript_end_sentence_index = i
                break
    else:
        transcript_start_sentence_index = clip_start_sentence_index
        transcript_end_sentence_index = clip_end_sentence_index

    clip_prompt = ""
    in_transcript = False
    for line in transcript_prompt.split("\n"):
        if line.startswith("#"):
            last_timestamp = line
            if in_transcript:
                clip_prompt += line + "\n"
        else:
            if line.startswith(f"{clip_start_sentence_index} "):
                clip_prompt += "<CLIP>\n"

            if line.startswith(f"{transcript_start_sentence_index} "):
                in_transcript = True
                clip_prompt += f"{last_timestamp}\n"
            elif line.startswith(f"{transcript_end_sentence_index} "):
                in_transcript = False

            if in_transcript:
                clip_prompt += line + "\n"

            if line.startswith(f"{clip_end_sentence_index} "):
                clip_prompt += "</CLIP>\n"
    return clip_prompt, sentence_timings


def format_transcript_by_time(transcript: list, start_time: int, end_time: int):
    clip_transcript = ""
    current_speaker = None

    for utterance in transcript:
        # Check if any part of the utterance overlaps with the clip time range
        if utterance["start"] < end_time and utterance["end"] > start_time:
            for word in utterance["words"]:
                # Check if the word is fully or partially within the clip time range
                if word["start"] < end_time and word["end"] > start_time:
                    # Add speaker label if it's a new speaker
                    if utterance["speaker"] != current_speaker:
                        clip_transcript += f"\n# Speaker {utterance['speaker']}\n"
                        current_speaker = utterance["speaker"]

                    clip_transcript += f"{word['text']} "

        # Break the loop if we've passed the end time
        elif utterance["start"] >= end_time:
            break

    return clip_transcript.strip()


def format_episode_description(description: str) -> str:
    import re

    # Remove common HTML tags
    description = re.sub(r"</?(?:p|span|em|br|a|strong)[^>]*>", "", description)

    # Remove hashtag phrases
    description = re.sub(r"#\w+", "", description)

    # Remove extra whitespace
    description = re.sub(r"\s+", " ", description).strip()

    # Remove links
    description = re.sub(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        "[LINK]",
        description,
    )

    if len(description) > 500:
        description = description[:497] + "..."

    return description


def get_clip_transcript_text(clip: Clip) -> str:
    transcript = get_audio_transcript(clip.feed_item.transcript_bucket_key)
    clip_transcript, _ = format_clip_prompt(
        transcript, {"start": clip.start_time, "end": clip.end_time}, max_mins=0
    )
    text = ""
    for line in clip_transcript.split("\n"):
        if line.startswith("<") or line.startswith("#") or line.strip() == "":
            continue
        else:
            _, line_text = line.split(" ", 1)
            text += line_text + " "
    return text.strip()
