import json
from web.lib.llm_client import llm_client
from web.models import FeedItem
from .transcript_utils import format_clip_prompt, format_episode_description
from langsmith import traceable


@traceable
def add_metadata(transcript: str, clip: dict, feed_item: FeedItem) -> dict:
    clip_prompt, _ = format_clip_prompt(transcript, clip)

    podcast_title = feed_item.feed.name
    episode_title = feed_item.name
    episode_description = format_episode_description(feed_item.body)

    # Only include lines between <CLIP> and </CLIP>
    clip_prompt = clip_prompt.split("<CLIP>")[1].split("</CLIP>")[0]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "submit_metadata",
                "description": "Submits the metadata for the clip.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The name of the clip. Should be concise and descriptive, no longer than 20 words without punctuation.",
                        },
                        "description": {
                            "type": "string",
                            "description": "A short summary of the clip. Should be a single paragraph less than 500 words.",
                        },
                    },
                    "required": ["name", "description"],
                },
            },
        }
    ]

    messages = [
        {
            "role": "system",
            "content": """You are an expert podcast producer. Your task is to generate a title and description for a viral podcast clip. You will be given a transcript of the clip and you need to generate a title and description that will be used to promote the clip on social media.""",
        },
        {
            "role": "user",
            "content": f"""<transcript>
{clip_prompt}
</transcript>
{f'<show>{podcast_title}</show>' if podcast_title else ''}
{f'<episode>{episode_title}</episode>' if episode_title else ''}
{f'<episode_description>{episode_description}</episode_description>' if episode_description else ''}
<instructions>
Based on the transcript, show, episode, and episode description, you need to generate:
1. Title: A concise and specific title for the clip
2. Description: A conscise, specific, and descriptive description for the clip

For the title:
- ALWAYS include specific details about people, events, and/or topics when possible from the transcript, show, episode, and/or description
- NEVER use colons or other punctuation in the title, it should be a single string of words that form a complete sentence
- Think of a hook that will draw users in on social media
- Create a title that accurately reflects the main topic or theme of the clip
- Keep it concise and 
- Limit it to no more than 20 words
- Ensure it captures the essence of the clip

Great example titles:
- Peter Thiel's Alternate Theories on Jeffrey Epstein and the Left Wing Philanthropy World
- Andrew Huberman Responds To Cannabis Drama
- Author Norman Ohler Reveals How the Nazi's Started Using Meth

Examples of terrible titles due to using punctuation with no specific details:
- Multiple Shooters Theory: Analyzing Audio Evidence from Recent Tragedy
- The Left Wing Philanthropy World: A Conversation with a Political Expert

For the description:
- Write a single paragraph (less than 500 words)
- Describe the topics of discussion in the clip
- Avoid generic phrases like "in the clip" or "the hosts talk about"
- Keep the description as information-dense as possible
- Focus solely on summarizing the content, without additional commentary

Once you have generated both the title and description, use the submit_metadata tool to provide this information. The tool requires two parameters:
1. "title": The clip name you created
2. "description": The summary you wrote

To use the tool, format your response like this:
<function_call>submit_metadata(title="Your clip name here", description="Your summary here")</function_call>

Remember to follow these instructions precisely. Do not include any additional text or explanations outside of the function call. Your entire response should consist solely of the function call with the name and summary you've created based on the transcript.
</instructions>""",
        },
    ]

    iters = 0
    max_iters = 10
    while iters < max_iters:
        iters += 1

        response = llm_client.chat.completions.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "submit_metadata"}},
            messages=messages,
        )

        try:
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if len(tool_calls) == 0:
                raise ValueError("No tool calls found in response")
            if len(tool_calls) > 1:
                raise ValueError("More than one tool call found in response")

            tool_call = tool_calls[0]
            if tool_call.function.name == "submit_metadata":
                arguments = json.loads(tool_call.function.arguments)
                name = arguments["title"]
                summary = arguments["description"]

                if name.strip() == "":
                    raise ValueError("Name cannot be empty")
                if len(name.split()) > 20:
                    raise ValueError("Name cannot be more than 20 words")

                clip["name"] = name
                clip["summary"] = summary
                return clip
            else:
                raise ValueError(f"Unexpected tool call: {tool_call.function.name}")
        except Exception as e:
            print(str(e))
            messages += [
                response_message,
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "submit_metadata",
                    "content": str(e),
                },
            ]
