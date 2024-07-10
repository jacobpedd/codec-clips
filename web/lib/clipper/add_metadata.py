import anthropic
from django.conf import settings
from .transcript_utils import format_transcript_view

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


def add_metadata(transcript, clip: dict) -> dict:
    transcript_view = format_transcript_view(transcript, clip["quote"], clip, 0, 0)

    tools = [
        {
            "name": "submit_metadata",
            "description": "Submits the metadata for the clip.",
            "input_schema": {
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
        }
    ]

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        system="\n".join(
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
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_metadata"},
        messages=[
            {"role": "user", "content": transcript_view},
        ],
    )

    if response.stop_reason == "tool_use":
        tool_use = next(block for block in response.content if block.type == "tool_use")
        tool_name = tool_use.name
        tool_input = tool_use.input
        if tool_name == "submit_metadata":
            clip["name"] = tool_input["name"]
            clip["summary"] = tool_input["summary"]
            return clip
        else:
            raise ValueError(f"Unexpected tool call: {tool_name}")
    else:
        raise ValueError(f"Unexpected stop reason: {response.stop_reason}")
