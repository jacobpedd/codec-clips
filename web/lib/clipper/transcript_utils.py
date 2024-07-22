import re
from thefuzz import fuzz


def format_transcript(transcript: list):
    formatted_transcript = ""
    for utterance in transcript:
        formatted_transcript += f"# Speaker {utterance['speaker']}\n"
        formatted_transcript += f"{utterance['text']}\n\n"
    return formatted_transcript


def format_transcript_by_time(transcript: list, start_time: int, end_time: int):
    clip_transcript = ""
    for utterance in transcript:
        if utterance["start"] > start_time and utterance["end"] < end_time:
            clip_transcript += f"{utterance['speaker']}\n"
            clip_transcript += f"{utterance['text']}\n"
    return clip_transcript


def format_transcript_view(
    transcript: list,
    quote: str,
    clip: dict | None = None,
    start_context_length=500,
    end_context_length=500,
) -> str:
    # Add global word index to each word in the transcript
    word_index = 0
    for utterance in transcript:
        for word in utterance["words"]:
            word["word_index"] = word_index
            word_index += 1
    total_words = word_index  # Total number of words in the transcript

    def get_transcript_between_indices(start_index, end_index):
        transcript_between_indices = ""
        for utterance in transcript:
            utterance_start_index = utterance["words"][0]["word_index"]
            utterance_end_index = utterance["words"][-1]["word_index"]

            if (
                start_index <= utterance_end_index
                and end_index >= utterance_start_index
            ):
                transcript_between_indices += f"# Speaker {utterance['speaker']}\n"
                words_in_range = [
                    word
                    for word in utterance["words"]
                    if start_index <= word["word_index"] <= end_index
                ]
                transcript_between_indices += " ".join(
                    [word["text"] for word in words_in_range]
                )
                transcript_between_indices += "\n\n"
        return transcript_between_indices

    # Find the start and end indices of the quote
    phrase = find_phrase(transcript, quote)
    quote_start_index = phrase["start_word_index"]
    quote_end_index = phrase["end_word_index"]
    quote_transcript = get_transcript_between_indices(
        quote_start_index, quote_end_index
    )

    # Find the start and end word indices of the clip
    if clip is None:
        content_start_index = quote_start_index
        content_end_index = quote_end_index
    else:
        # Find the start and end indices of the clip
        clip_start_phrase_start_index = find_phrase(transcript, clip["start_quote"])[
            "start_word_index"
        ]
        content_start_index = clip_start_phrase_start_index
        clip_end_index = find_phrase(transcript, clip["end_quote"])["end_word_index"]
        content_end_index = clip_end_index

    final_transcript = ""
    # Add start context if needed
    if start_context_length > 0:
        # Add context to the start of the clip
        context_start_index = max(0, content_start_index - start_context_length)
        # Construct the transcript string with context
        context_start_transcript = get_transcript_between_indices(
            context_start_index, content_start_index - 1
        )
        if context_start_index == 0:
            final_transcript += "<TRANSCRIPT START>\n"
        else:
            final_transcript += "<CONTEXT START>\n"
        final_transcript += context_start_transcript

    # Add the clip -> start of quote if there is a clip
    if clip is not None:
        final_transcript += "\n<CLIP>\n"
        if content_start_index != quote_start_index:
            clip_start_transcript = get_transcript_between_indices(
                content_start_index, quote_start_index
            )
            final_transcript += clip_start_transcript

    # Add the quote to the transcript
    final_transcript += "\n<QUOTE>\n"
    final_transcript += quote_transcript
    final_transcript += "\n</QUOTE>\n"

    # Add the end of quote -> end of clip if there is a clip
    if clip is not None:
        if content_end_index != quote_end_index:
            clip_end_transcript = get_transcript_between_indices(
                quote_end_index + 1, content_end_index
            )
            final_transcript += clip_end_transcript
        final_transcript += "\n</CLIP>\n"

    # Add end context if needed
    if end_context_length > 0:
        # Add context to the end of the clip
        context_end_index = min(total_words - 1, content_end_index + end_context_length)
        # Construct the transcript string with context
        context_end_transcript = get_transcript_between_indices(
            content_end_index + 1, context_end_index
        )
        final_transcript += context_end_transcript
        if context_end_index == total_words - 1:
            final_transcript += "<TRANSCRIPT STOP>\n"
        else:
            final_transcript += "<CONTEXT END>\n"
    return final_transcript


def find_phrase(transcript: list, phrase: str, start_from=0, end_at=None):
    # We only care about timing, so we can just loop through all the words
    words = []
    for utterance in transcript:
        words += utterance["words"]

    if end_at is None:
        end_at = len(words)

    phrase_words = phrase.split()
    best_match = (-1, 0)  # (index, score)

    for i in range(start_from, end_at - len(phrase_words) + 1):
        candidate = " ".join(
            word["text"].lower() for word in words[i : i + len(phrase_words)]
        )
        candidate = re.sub(r"[^\w\s]", "", candidate)
        score = fuzz.ratio(phrase, candidate)

        if score > best_match[1]:
            best_match = (i, score)

    if best_match[1] > 80:  # NOTE: Threshold for matching, set based on vibes
        best_match_index = best_match[0]
        best_match_end_index = best_match_index + len(phrase_words) - 1
        start_word = words[best_match_index]
        end_word = words[best_match_end_index]
        return {
            "start_word_index": best_match_index,
            "end_word_index": best_match_end_index,
            "start": start_word["start"],
            "end": end_word["end"],
        }
    else:
        print(f"Error finding phrase, best score was {best_match[1]} out of {90}")
        print(f"Original phrase: {phrase}")
        print(
            f"Best match:      {' '.join(word['text'] for word in words[best_match[0]:best_match[0]+len(phrase_words)]).lower()}"
        )
        raise ValueError("Error finding phrase")
