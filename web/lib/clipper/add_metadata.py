import json
from braintrust import traced
from web.lib.llm_client import llm_client
from .transcript_utils import format_transcript_view


@traced
def add_metadata(transcript, clip: dict) -> dict:
    transcript_view = format_transcript_view(transcript, clip["quote"], clip, 0, 0)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "submit_metadata",
                "description": "Submits the metadata for the clip.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the clip. Should be concise and descriptive, no longer than 20 words.",
                        },
                        "summary": {
                            "type": "string",
                            "description": "A short summary of the clip. Should be a single paragraph (<500 words), enumerating major topics and describing the tone.",
                        },
                    },
                    "required": ["name", "summary"],
                },
            },
        }
    ]

    response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_metadata"},
        messages=[
            {
                "role": "system",
                "content": "\n".join(
                    [
                        "You are a helpful assistant who adds metadata to a clip.",
                        "# TASK",
                        "You are helping the user, the podcast host, by adding metadata to a clip from their podcast.",
                        "The user will provide the transcript of the clip in their message.",
                        "You will add metadata to the clip, with the following properties:",
                        "- name: The name of the clip",
                        "- summary: A short summary of the clip",
                        "# NAME",
                        "The name of the clip is based on the content of the transcript.",
                        "It should be a concise and descriptive name that accurately reflects the content of the clip.",
                        "The name should be no longer than 20 words.",
                        "# SUMMARY",
                        "Single paragraph (<500 words)",
                        "Enumerate all major topics discussed.",
                        "Colorfully describe the tone. Is it funny, informational, spicy?",
                        "Do not include any context like 'in the clip' or 'the hosts talk about'.",
                        "Keep as information dense as possible.",
                        "Don't include any non-summary text",
                        "# RESPONSE",
                        "Use the submit_metadata tool to provide the name and summary for the clip.",
                    ]
                ),
            },
            {"role": "user", "content": transcript_view},
        ],
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if len(tool_calls) == 0:
        raise ValueError("No tool calls found in response")
    if len(tool_calls) > 1:
        raise ValueError("More than one tool call found in response")

    tool_call = tool_calls[0]
    if tool_call.function.name == "submit_metadata":
        arguments = json.loads(tool_call.function.arguments)
        clip["name"] = arguments["name"]
        clip["summary"] = arguments["summary"]
        return clip
    else:
        raise ValueError(f"Unexpected tool call: {tool_call.function.name}")
