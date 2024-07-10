import anthropic
from codec import settings
from .transcript_utils import find_phrase, format_transcript

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


def suggest_moments(transcript):
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    tools = [
        {
            "name": "submit_moments",
            "description": "Submits the moment array that the assistant has identified to the user for review. There should be at least 3 moments and no more than 10.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "moments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "A one-sentence description of the moment to help capture why it was selected.",
                                },
                                "quote": {
                                    "type": "string",
                                    "description": "A unique, exact quote to identify the moment's location in the transcript. This will be used by a pythons script to locate the moment in the transcript. There will be an error if the quote is not found in the transcript.",
                                },
                            },
                            "required": ["name", "quote"],
                        },
                    }
                },
                "required": ["moments"],
            },
        }
    ]

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        system="\n".join(
            [
                "# Role and Context",
                "You are an AI assistant helping podcast hosts and editors find clip-worthy moments within show transcripts. These moments will be used to create 3-10 minute YouTube clips.",
                "",
                "# Task",
                "Identify compelling moments in podcast transcripts for short-form video content.",
                "",
                "# Input",
                "The user will provide a podcast transcript with speaker labels. The transcript may contain errors due to speech-to-text conversion.",
                "",
                "# Moment Criteria",
                "- Identify 3-10 non-overlapping moments per transcript",
                "- Exclude show intros, outros, and advertisements",
                "- Focus on engaging, informative, or entertaining segments",
                "- Focus on segments that are likely to go viral",
                "- Prioritize moments that can stand alone without extensive context",
                "- Consider segments with strong emotional impact, surprising facts, or humorous exchanges",
                "- Moments will be used by the editor to create a 3-10 minute clip",
                "- Do not let the moment clips overlap",
                "",
                "# Output Format",
                "Use the moment tool to submit the moments to the user for review.",
            ]
        ),
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_moments"},
        messages=[
            {
                "role": "user",
                "content": f"<transcript>{format_transcript(transcript)}</transcript>",
            },
        ],
    )

    moments_response = None
    for content in response.content:
        if content.type == "tool_use" and content.name == "submit_moments":
            moments_response = content.input
            break

    moments = moments_response["moments"]

    # Find word index for each moment
    # TODO: send errors back to model and retry?
    for moment in moments:
        find_phrase(transcript, moment["quote"])

    return moments
