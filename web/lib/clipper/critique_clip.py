import json
from web.lib.llm_client import llm_client
from langsmith import traceable


def critique_clip(clip_prompt: str, clip: dict) -> str | None:
    start_critique = critique_clip_start(clip_prompt, clip)
    end_critique = critique_clip_end(clip_prompt, clip)
    return apply_critiques(start_critique, end_critique, clip)


@traceable
def critique_clip_start(clip_prompt: str, clip: dict) -> str | None:
    # We only want the text before </Clip> including the <CLIP> tag
    # transcript_view = transcript_view.split("</CLIP>")[0]
    start_clip_prompt = clip_prompt.split("</CLIP>")[0] + "</CLIP>"
    duration_ms = clip["end"] - clip["start"]
    duration_seconds = duration_ms / 1000.0
    duration_minutes = duration_seconds / 60.0
    metadata = {
        "start_index": clip["start_index"],
        "end_index": clip["end_index"],
        "duration_minutes": duration_minutes,
    }
    response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "You are an AI assistant helping a podcast host edit viral clips for their YouTube channel. Your task is to critique the starting position of a clip within a provided transcript.",
                        "",
                        "Here is the podcast transcript:",
                        "<transcript>",
                        start_clip_prompt,
                        "</transcript>",
                        "",
                        "Your task is to evaluate whether the current starting position of the clip is appropriate based on the following criteria:",
                        "- The first sentence should introduce the topic of the clip.",
                        "- There should be a hook in the first few sentences to grab the listener's attention.",
                        "- Listeners should not be confused about what the hosts are discussing when they start listening.",
                        "- If not near the 2-minute time limit, look for ways to trim the beginning if there's a more engaging start point.",
                        "- The clip should be between 2 and 10 minutes long.",
                        "- The listeners can't hear anything outside the <CLIP> tags.",
                        "",
                        "To complete this task:",
                        "1. Identify the current clip boundaries using the provided start and end indices:",
                        f"   <clip_start>{metadata['start_index']}</clip_start>",
                        f"   <clip_end>{metadata['end_index']}</clip_end>",
                        f"   <clip_duration_minutes>{metadata['duration_minutes']}</clip_duration_minutes>",
                        "",
                        "2. Read through the transcript, paying close attention to the content before the current clip start.",
                        "",
                        "3. Evaluate whether the current starting position meets the criteria mentioned above.",
                        "",
                        "4. If a change in the starting position is needed, identify a new, more appropriate start index.",
                        "",
                        "5. Provide your critique and recommendation in the following format:",
                        "   <critique>",
                        "   [Do the first couple of sentences give context to orient the listener?]",
                        "   [What is the hook that will grab the listener's attention?]",
                        "   [Does a change need to be made?]",
                        "   [Can you make the change without violating timing requirements?]",
                        "   </critique>",
                        "   ",
                        "   <recommendation>",
                        "   [If proposing a change, provide the new start index here. If no change is needed, write 'No change recommended.']",
                        "   </recommendation>",
                        "",
                        "Remember to keep your response concise and focused solely on the starting position of the clip. Do not critique any other aspects of the clip or transcript.",
                    ]
                ),
            },
        ],
    )
    return response.choices[0].message.content


@traceable
def critique_clip_end(clip_prompt: str, clip: dict) -> str | None:
    # We only want the text before </Clip> including the <CLIP> tag
    clip_prompt = clip_prompt.split("<CLIP>")[1] + "<CLIP>"
    clip_duration_ms = clip["end"] - clip["start"]
    clip_duration_seconds = clip_duration_ms / 1000.0
    clip_minutes = clip_duration_seconds / 60.0
    metadata = {
        "start_index": clip["start_index"],
        "end_index": clip["end_index"],
        "duration_minutes": clip_minutes,
    }

    response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "\n".join(
                            [
                                "You are an AI assistant helping a podcast host edit viral clips for their YouTube channel. Your task is to critique the ending position of a clip within a provided transcript.",
                                "",
                                "Here is the podcast transcript:",
                                "<transcript>",
                                clip_prompt,
                                "</transcript>",
                                "",
                                "Your task is to evaluate whether the current ending position of the clip is appropriate based on the following criteria:",
                                "- The clip should end with a natural conclusion to the discussion.",
                                "- Avoid ending the clip in the middle of a conversation topic.",
                                "- If there's very compelling conversation after the clip, consider extending the clip to include it.",
                                "- The clip should be between 2 and 10 minutes long.",
                                "",
                                "To complete this task:",
                                "1. Identify the current clip boundaries using the provided start and end indices:",
                                f"   <clip_start>{metadata['start_index']}</clip_start>",
                                f"   <clip_end>{metadata['end_index']}</clip_end>",
                                f"   <clip_duration_minutes>{metadata['duration_minutes']}</clip_duration_minutes>",
                                "",
                                "2. Read through the transcript, paying close attention to the content after the current clip end.",
                                "",
                                "3. Evaluate whether the current ending position meets the criteria mentioned above.",
                                "",
                                "4. If a change in the ending position is needed, identify a new, more appropriate end index.",
                                "",
                                "5. Provide your critique and recommendation in the following format:",
                                "   <critique>",
                                "   [Does the clip end with a natural conclusion to the topic?]",
                                "   [Is there a point in the clip that users might get bored and stop listening?]",
                                "   [Is there a compelling conversation after the clip ends that makes sense to include?]",
                                "   [Can you make the change without making the clip too long or too short?]",
                                "   </critique>",
                                "   ",
                                "   <recommendation>",
                                "   [If proposing a change, provide the new end index here. If no change is needed, write 'No change recommended.']",
                                "   </recommendation>",
                                "",
                                "Remember to keep your response concise and focused solely on the ending position of the clip. Do not critique any other aspects of the clip or transcript.",
                            ]
                        )
                    ]
                ),
            },
        ],
    )
    return response.choices[0].message.content


@traceable
def apply_critiques(start_critique: str, end_critique: str, clip: dict) -> str | None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "submit_clips",
                "description": "Submits the finalized clip according to the critiques.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_index": {
                            "type": "integer",
                            "description": "The sentence index where the clip should start.",
                        },
                        "end_index": {
                            "type": "integer",
                            "description": "The sentence index where the clip should end.",
                        },
                    },
                    "required": ["start_index", "end_index"],
                },
            },
        }
    ]

    clip_duration_ms = clip["end"] - clip["start"]
    clip_duration_seconds = clip_duration_ms / 1000.0
    clip_minutes = clip_duration_seconds / 60.0
    metadata = {
        "start_index": clip["start_index"],
        "end_index": clip["end_index"],
        "duration_minutes": clip_minutes,
    }

    response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_clips"},
        messages=[
            {
                "role": "system",
                "content": "\n".join(
                    [
                        "# Role and Context",
                        "You are an AI assistant helping a podcast host edit viral clips for their YouTube channel.",
                        "",
                        "# Task",
                        "You are take critiques from the editors and apply them using the submit_clips tool.",
                        "",
                        "# Input",
                        "The user will provide critiques from the editors and the metadata for the clip.",
                        "The metadata will include the origional start and end indices of the clip.",
                        "There will be separate critiques for the start and end of the clip.",
                        "",
                        "# Instructions",
                        "If the critiques mention a change in the start or end index, use the submit_clips tool to submit the clip with the new index.",
                        "If a critique does not require a change, use the index form the metadata.",
                        "",
                        "# Output Format",
                        "You must call the submit_clips tool exactly once.",
                    ]
                ),
            },
            {
                "role": "user",
                "content": f"<metadata>{json.dumps(metadata, indent=2)}</metadata>\n<start_critique>{start_critique}</start_critique>\n<end_critique>{end_critique}</end_critique>",
            },
        ],
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if not tool_calls or len(tool_calls) != 1:
        raise ValueError(
            "Error: Invalid tool calls. You must call the submit_clips tool exactly once."
        )

    tool_call = tool_calls[0]

    if tool_call.function.name != "submit_clips":
        raise ValueError(
            "Error: Invalid tool call. You must call the submit_clips tool exactly once."
        )

    args = json.loads(tool_call.function.arguments)
    if "start_index" not in args or "end_index" not in args:
        raise ValueError(
            "Error: Invalid function arguments. Please ensure your JSON is correctly formatted and includes the 'start_index' and 'end_index' keys."
        )

    clip["start_index"] = args["start_index"]
    clip["end_index"] = args["end_index"]

    return clip
