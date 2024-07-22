import json
from braintrust import traced
from web.lib.llm_client import llm_client
from .transcript_utils import find_phrase, format_transcript_view


@traced
def suggest_clip(
    transcript: dict, moment: dict, clip: dict | None, feedback: str | None
) -> dict:
    tools = [
        {
            "type": "function",
            "function": {
                "description": "Submits the clip object that the assistant has identified to the user for review.",
                "name": "submit_clip",
                "parameters": {
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
                            "description": "A unique, exact quote to identify the start of the clip. This will be used by a python script to locate the clip in the transcript. There will be an error if the quote is not found in the transcript. Quotes should be the minimum length required to be unique. They should not include any tags or speaker labels.",
                        },
                        "end_quote": {
                            "type": "string",
                            "description": "A unique, exact quote to identify the end of the clip. The last word of the quote will be the last word of the clip. This will be used by a python script to locate the clip in the transcript. There will be an error if the quote is not found in the transcript. Quotes should be the minimum length required to be unique. They should not include any tags or speaker labels.",
                        },
                    },
                    "required": ["reasoning", "name", "start_quote", "end_quote"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "description": "Edits the view of the transcript surrounding the clip so the assistant can see more or less of the context surrounding the clip. The function returns a new transcript string with the adjusted context.",
                "name": "edit_transcript_context",
                "parameters": {
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
        response = llm_client.chat.completions.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            tools=tools,
            tool_choice="required",
            messages=messages,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if len(tool_calls) == 0:
            raise ValueError("No tool calls found in response")
        if len(tool_calls) > 1:
            raise ValueError("More than one tool call found in response")

        tool_call = tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        if tool_call.function.name == "edit_transcript_context":
            print(
                f"Model called {tool_call.function.name}({tool_call.function.arguments}): {tool_call.function.arguments}"
            )
            start_context_length += int(arguments["start_change"])
            end_context_length += int(arguments["end_change"])
            transcript_view = format_transcript_view(
                transcript,
                moment["quote"],
                None,
                start_context_length,
                end_context_length,
            )
            messages += [
                {"role": "assistant", "tool_calls": tool_calls},
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": transcript_view,
                },
            ]
        elif tool_call.function.name == "submit_clip":
            find_phrase(transcript, arguments["start_quote"])
            find_phrase(transcript, arguments["end_quote"])
            return {
                "name": arguments["name"],
                "start_quote": arguments["start_quote"],
                "end_quote": arguments["end_quote"],
            }
        else:
            raise ValueError(
                f"Suggest clip model called unknown tool: {tool_call.function.name}"
            )
