import json
from typing import Dict, Any
from web.lib.llm_client import llm_client
from .transcript_utils import (
    format_transcript_prompt,
)
from langsmith import traceable

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "submit_clips",
            "description": "Submits the clips array that the assistant has identified to the user for review. The clips array should be between 1 and 3 items long. These should be the top 3 most compelling clips from the transcript, each between 2 and 10 minutes long. The start and end indices should come from the transcript sentence indices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clips": {
                        "type": "array",
                        "description": "The top 3 most compelling clips from the transcript. If there aren't enough clips, you can submit 1 or 2 clips. Each clip MUST be between 2 and 10 minutes long.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content_reasoning": {
                                    "type": "string",
                                    "description": "A short explanation of why this clip's content is compelling and likely to go viral on YouTube.",
                                },
                                "duration_reasoning": {
                                    "type": "string",
                                    "description": "An explanation of why this clip's duration is between 2 and 10 minutes.",
                                },
                                "start_reasoning": {
                                    "type": "string",
                                    "description": "An explanation of why this clip starts at this sentence index.",
                                },
                                "end_reasoning": {
                                    "type": "string",
                                    "description": "An explanation of why this clip ends at this sentence index.",
                                },
                                "start_index": {
                                    "type": "integer",
                                    "description": "The sentence index where the clip should start.",
                                },
                                "end_index": {
                                    "type": "integer",
                                    "description": "The sentence index where the clip should end.",
                                },
                            },
                            "required": ["reasoning", "start_index", "end_index"],
                        },
                    }
                },
                "required": ["clips"],
            },
        },
    }
]


@traceable
def generate_clips(transcript: str, show: str = None, episode: str = None, description: str = None, max_iters: int = 10) -> tuple:
    transcript_prompt, sentence_timings = format_transcript_prompt(transcript)
    messages = [
        {
            "role": "system",
            "content": f"You are an expert podcast producer for the podcast show, {show}. Your task is to identify viral clips from the transcript of their podcast episode, {episode}. The clips must be at least 3 minutes in length and no longer than 10 minutes. The clips will be posted to the official {show} YouTube channel.",
        },
        {
            "role": "user",
            "content": f'''<transcript>
{transcript_prompt}
</transcript>
{f'<show>{show}</show>' if show else ''}
{f'<episode>{episode}</episode>' if episode else ''}
{f'<episode_description>{description}</episode_description>' if description else ''}
<instructions>
Based on the transcript with the context of the show, episode, and episode description, identify up to 3 compelling viral clips that will be posted to the official {show} YouTube channel.

Transcript format:
- The podcast transcript contains speaker labels and sentence indexing
- The speaker labels are alphanumeric
- Each utterance starts with a header in the format: '# [Speaker] [Timestamp]'
- Timestamps are in mm:ss format or h:mm:ss format.
- Each sentence within an utterance is preceded by a numeric index
- The transcript may contain errors due to speech-to-text conversion. Occasionally, the transcript is unable to distinguish between speakers

Clip selection criteria:
- Clips must be between 3 and 10 minutes in length
- Clips must be self-contained and entertaining without the rest of the transcript since they will be listened to with no context
- Clips should discuss separate topics, if possible
- Clips must not overlap
- Prioritize quality over quantity. It's better to submit 1 or 2 excellent clips than 3 mediocre ones
- Clips must be compelling and likely to go viral on YouTube
- NEVER include the show's intro, outro, advertisements, promotions, beginning, or ending in a clip
- NEVER start or end clips in the middle of a topic

Submitting clips:
- Use the submit_clips tool to submit the clips to the user for review
- Provide the start and end sentence indices for each clip.
- These indices should correspond directly to the sentence numbers in the transcript
- Avoid overlapping clips by choosing clips that are far apart in the transcript
- If any of the above criteria are not met for any clips, submit_clips will return an error with instructions on how to fix the issue
- Keep working on the clips until the submission is successful
- You should provide reasoning as to why you selected the content, duration, start, and end indices for each clip

Example of a great clip:
{{
    "content_reasoning": "This clip discusses a surprising fact about the guest's workout routine, which contradicts public perception. It's likely to generate interest and discussion.",
    "duration_reasoning": "The clip is approximately 5 minutes long, falling within the 3-10 minute range.",
    "start_reasoning": "The clip starts with the introduction of the guest's workout routine, setting up the context for the clip.",
    "end_reasoning": "The clip ends with the guest's workout routine and ways to incorporate it into one's own fitness regimen, providing a comprehensive overview of the topic.",
    "start_index": 45,
    "end_index": 110,
}}

Example of a bad clip due to starting at the beginning of the show, overlapping with the previous clip (end_index > start_index of previous clip), and poor reasoning on why the start and end indices are selected:
{{
    "content_reasoning": "This clip discusses the guest's workout routine, which contradicts public perception. It's likely to generate interest and discussion.",
    "duration_reasoning": "The clip is approximately 5 minutes long, falling within the 3-10 minute range.",
    "start_reasoning": "The clip starts at sentence index 0, which is the beginning of the show.",
    "end_reasoning": "The clip ends at sentence index 52, which is the end of the show.",
    "start_index": 0,
    "end_index": 52,
}}

You will be FIRED if you submit clips that do not meet the criteria, aren't supported by reasoning, overlap with other clips, or are not interesting enough to go viral on YouTube.
</instructions>''',
        },
        # {
        #     "role": "assistant",
        #     "content": "Based on the transcript, here are compelling clips I've identified to submit to the submit_clips tool that meet the criteria:"
        # }
    ]

    for iters in range(max_iters):
        print(f"\nIteration {iters + 1}")

        response = llm_client.chat.completions.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            tools=TOOLS,
            tool_choice={"type": "function", "function": {"name": "submit_clips"}},
            messages=messages,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls or len(tool_calls) != 1:
            error_message = "Error: Invalid tool calls. You must call the submit_clips tool exactly once."
            print(f"  {error_message}")
            messages.extend(
                [response_message, {"role": "user", "content": error_message}]
            )
            continue

        tool_call = tool_calls[0]

        try:
            args = json.loads(tool_call.function.arguments)
            clips = args["clips"]
            print(f"  Received {len(clips)} clip(s) from the model")
        except (json.JSONDecodeError, KeyError):
            error_message = "Error: Invalid function arguments. Please ensure your JSON is correctly formatted and includes the 'clips' key."
            print(f"  {error_message}")
            messages.extend(
                [response_message, create_tool_result(tool_call.id, error_message)]
            )
            continue

        valid_clip_message = ""
        validation_errors = []
        validated_clips = []

        for i, clip in enumerate(clips):
            try:
                validated_clip = validate_clip(clip, sentence_timings)
                validated_clips.append(validated_clip)
                valid_clip_message += (
                    f"Clip {i + 1}: Successful. Keep this clip as is.\n"
                )
                print(f"  Clip {i + 1} validated successfully")
            except ValueError as e:
                validation_errors.append((i, str(e)))
                print(f"  Clip {i + 1} validation error: {str(e)}")

        if len(validated_clips) < 2 and len(validation_errors) > 0:
            error_message = ""
            if valid_clip_message.strip() != "":
                error_message += (
                    f"Clips that were validated successfully:\n{valid_clip_message}"
                )
            error_message += "Clip validation errors:\n" + "\n".join(
                [f"Clip {i + 1}: {error}" for i, error in validation_errors]
            )
            error_message += (
                "\nPlease adjust invalid clips and try submitting them again."
            )
            print("  Validation errors found. Requesting model to retry.")
            messages.extend(
                [response_message, create_tool_result(tool_call.id, error_message)]
            )
            continue

        # Check for overlapping clips
        overlap_found = False
        for i in range(len(validated_clips)):
            for j in range(i + 1, len(validated_clips)):
                if (
                    validated_clips[i]["start_index"] < validated_clips[j]["end_index"]
                    and validated_clips[j]["start_index"]
                    < validated_clips[i]["end_index"]
                ):
                    error_message = f"Error: Clips {i + 1} and {j + 1} overlap. Please ensure clips do not overlap. If both clips are about the same thing, you can submit them as a single clip."
                    print(f"  {error_message}")
                    messages.extend(
                        [
                            response_message,
                            create_tool_result(tool_call.id, error_message),
                        ]
                    )
                    overlap_found = True
                    break
            if overlap_found:
                break

        if overlap_found:
            continue

        print(f"  Successfully generated {len(validated_clips)} valid clip(s)")
        return validated_clips, iters + 1

    print("Exceeded maximum iterations")
    raise ValueError("Exceeded max iterations for submit_clips")


def validate_clip(
    clip: Dict[str, Any], sentence_timings: Dict[int, Dict[str, int]]
) -> Dict[str, Any]:
    if "start_index" not in clip or "end_index" not in clip:
        raise ValueError("Both start_index and end_index must be provided.")

    start_index = clip["start_index"]
    end_index = clip["end_index"]

    if start_index not in sentence_timings or end_index not in sentence_timings:
        raise ValueError(
            "Invalid start_index or end_index. Ensure they correspond to sentence indices in the transcript."
        )

    if start_index >= end_index:
        raise ValueError("start_index must be less than end_index.")

    clip["start"] = sentence_timings[start_index]["start"]
    clip["end"] = sentence_timings[end_index]["end"]
    clip_duration_minutes = (clip["end"] - clip["start"]) / 60000.0

    if clip_duration_minutes < 2:
        raise ValueError(
            f"Duration is too short ({clip_duration_minutes:.2f} minutes). Please extend the clip to at least 2 minutes by adjusting both start_index and end_index."
        )
    elif clip_duration_minutes > 10:
        raise ValueError(
            f"Duration is too long ({clip_duration_minutes:.2f} minutes). Please shorten the clip to at most 10 minutes by adjusting both start_index and end_index."
        )

    return clip


def create_tool_result(tool_call_id: str, content: str) -> Dict[str, Any]:
    if not content:
        raise ValueError("Content cannot be empty")
    if content.strip() == "":
        raise ValueError("Content cannot be empty string")
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": "submit_clips",
        "content": content,
    }
