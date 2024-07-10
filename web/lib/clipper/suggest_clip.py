import anthropic
from codec import settings
from .transcript_utils import find_phrase, format_transcript, format_transcript_view

client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    base_url="https://anthropic.hconeai.com/",
    default_headers={
        "Helicone-Auth": f"Bearer {settings.HELICONE_API_KEY}",
        "Helicone-Cache-Enabled": "true",
        "Helicone-User-Id": "clipper",
        "Helicone-Retry-Enabled": "true",
    },
)


def suggest_clip(
    transcript: dict, moment: dict, clip: dict | None, feedback: str | None
) -> dict:
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    tools = [
        {
            "name": "submit_clip",
            "description": "Submits the clip object that the assistant has identified to the user for review.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A one-sentence explanation of why you called the tool the way you did.",
                    },
                    "name": {
                        "type": "string",
                        "description": "A one-sentence description of the clip to give the user context for why it was selected.",
                    },
                    "start_quote": {
                        "type": "string",
                        "description": "A unique, exact quote to identify the start of the clip. This will be used by a pythons script to locate the clip in the transcript. There will be an error if the quote is not found in the transcript. Quotes should be the minimum length required to be unique. They should not include any tags or speaker labels.",
                    },
                    "end_quote": {
                        "type": "string",
                        "description": "A unique, exact quote to identify the end of the clip. The last word of the quote will be the last word of the clip. This will be used by a pythons script to locate the clip in the transcript. There will be an error if the quote is not found in the transcript. Quotes should be the minimum length required to be unique. They should not include any tags or speaker labels.",
                    },
                },
                "required": ["reasoning", "name", "start_quote", "end_quote"],
            },
        },
        {
            "name": "edit_transcript_context",
            "description": "Edits the view of the transcript surrounding the clip so the assistant can see more or less of the context surrounding the clip. The function returns a new transcript string with the adjusted context.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A one-sentence explanation of why you called the tool the way you did.",
                    },
                    "start_change": {
                        "type": "integer",
                        "description": "The number of words to add or remove from the start of the transcript. A negative number will remove words, a positive number will add words.",
                    },
                    "end_change": {
                        "type": "integer",
                        "description": "The number of words to add or remove from the end of the transcript. A negative number will remove words, a positive number will add words.",
                    },
                },
                "required": ["reasoning", "start_change", "end_change"],
            },
        },
    ]

    generating = True
    start_context_length = 2000
    end_context_length = 2000
    transcript_view = format_transcript_view(
        transcript, moment["quote"], None, start_context_length, end_context_length
    )

    messages = []
    if clip is not None and feedback is not None:
        messages = [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        f"Clip name: {moment['name']}",
                        f"Transcript view:",
                        transcript_view,
                        f"Feedback:",
                        feedback,
                    ]
                ),
            }
        ]
    elif clip is None and feedback is None:
        messages = [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        f"Clip name: {moment['name']}",
                        f"Transcript view:",
                        transcript_view,
                    ]
                ),
            }
        ]
    else:
        raise ValueError("Clip and feedback should both be None or both be set")

    while generating:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            system="\n".join(
                [
                    "# Role and Context",
                    "You are an AI assistant helping podcast hosts edit viral clips form their podcast transcript. The clips are based on their podcast transcript and posted to their YouTube channel.",
                    "",
                    "# Task",
                    "Choose the start and end points of the clip based on the transcript and the users feedback.",
                    "",
                    "# Input",
                    "The user will provide a one sentence description of the clip and the relevant transcript with speaker labels.",
                    "The transcript will have the following sections denoted by <tags>:",
                    "- <TRANSCRIPT START>: Denotes the start and end of the transcript. Your transcript will only contain this tag if it starts at the beginning of the podcast transcript.",
                    "- <TRANSCRIPT STOP>: Denotes the end of the transcript. Your transcript will only contain this tag if it ends at the end of the podcast transcript.",
                    "- <CONTEXT START>: Denotes the start of the context surrounding the clip. Your transcript will only contain this tag if it does not start at the beginning of the podcast transcript.",
                    "- <CONTEXT END>: Denotes the end of the context surrounding the clip. Your transcript will only contain this tag if it does not end at the end of the podcast transcript.",
                    "- <CLIP>: Opening and closing the tag denotes the start and end of the currently selected clip. If there is no clip selected, you need to use the submit_clip tool to submit the first clip.",
                    "- <QUOTE>: Opening and closing the tag denotes the start and end of a quote in the transcript. The quote is the key moment in the clip that the user wants to center the clip around.",
                    "",
                    "# Clip Criteria",
                    "- Be a 3-10 minutes in length",
                    "- Have enough context to stand alone when played without any additional content",
                    "- Exclude show intros, outros, and advertisements",
                    "- Only include the nessasary context to capture the moment",
                    "- Find a place to start the clip that gives the reader enough context to understand the discussion",
                    "- Find a place to end the clip that is a natural conclusion to the discussion",
                    "",
                    "# Response",
                    "Use the tools provided to create the clip and edit the transcript context if needed.",
                    "If you need to change your view of the transcript, use edit_transcript_context to edit the start end and end of the context surrounding the clip.",
                    "When you have enough context, use submit_clip to submit the clip.",
                    "When you submit clip, only the content between the start and end quotes will be used. The users will not see the surrounding context.",
                    "Remember to look at the exact schema for the tools you are using and submit the correct input.",
                ]
            ),
            tools=tools,
            tool_choice={"type": "any"},
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_use = next(
                block for block in response.content if block.type == "tool_use"
            )
            tool_name = tool_use.name
            tool_input = tool_use.input
            if tool_name == "edit_transcript_context":
                print(
                    f"Model called {tool_name}({tool_input['start_change']}, {tool_input['end_change']}): {tool_input['reasoning']}"
                )
                start_context_length += tool_input["start_change"]
                end_context_length += tool_input["end_change"]
                transcript_view = format_transcript_view(
                    transcript,
                    moment["quote"],
                    None,
                    start_context_length,
                    end_context_length,
                )
                messages += [
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": transcript_view,
                            }
                        ],
                    },
                ]
            elif tool_name == "submit_clip":
                find_phrase(transcript, tool_input["start_quote"])
                find_phrase(transcript, tool_input["end_quote"])
                return {
                    "name": tool_input["name"],
                    "start_quote": tool_input["start_quote"],
                    "end_quote": tool_input["end_quote"],
                }
            else:
                raise ValueError(f"Suggest clip model called unknown tool: {tool_name}")
        else:
            raise ValueError(
                f"Suggest clip model stopped without submitting clip: {response.stop_reason}"
            )
