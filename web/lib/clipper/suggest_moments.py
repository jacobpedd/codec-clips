import json
from braintrust import traced
from web.lib.llm_client import llm_client
from .transcript_utils import find_phrase, format_transcript


@traced
def suggest_moments(transcript):
    tools = [
        {
            "type": "function",
            "function": {
                "description": "Submits the moment array that the assistant has identified to the user for review. There should be at least 3 moments and no more than 10.",
                "name": "submit_moments",
                "parameters": {
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
                                        "description": "A unique, exact quote to identify the moment's location in the transcript. This will be used by a python script to locate the moment in the transcript. There will be an error if the quote is not found in the transcript.",
                                    },
                                },
                                "required": ["name", "quote"],
                            },
                        }
                    },
                    "required": ["moments"],
                },
            },
        }
    ]

    response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_moments"},
        messages=[
            {
                "role": "system",
                "content": "\n".join(
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
            },
            {
                "role": "user",
                "content": f"<transcript>{format_transcript(transcript)}</transcript>",
            },
        ],
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if len(tool_calls) == 0:
        raise ValueError("No tool calls found in response")
    if len(tool_calls) > 1:
        raise ValueError("More than one tool call found in response")

    tool_call = tool_calls[0]
    moments = json.loads(tool_call.function.arguments)["moments"]

    print(json.dumps(moments, indent=2))

    # Find word index for each moment
    # TODO: send errors back to model and retry?
    for moment in moments:
        find_phrase(transcript, moment["quote"])

    return moments
