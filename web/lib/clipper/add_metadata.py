import json
from web.lib.llm_client import llm_client
from .transcript_utils import format_clip_prompt
from langsmith import traceable


@traceable
def add_metadata(transcript, clip: dict) -> dict:
    clip_prompt, _ = format_clip_prompt(transcript, clip)
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

    messages = [
        {
            "role": "user",
            "content": "\n".join(
                [
                    "You are an AI assistant tasked with adding metadata to a podcast clip. Your job is to analyze the transcript of the clip and generate appropriate metadata. Here are your instructions:",
                    "",
                    "First, carefully read and analyze the following transcript:",
                    "",
                    "<transcript>",
                    f"{clip_prompt}",
                    "</transcript>",
                    "",
                    "Based on this transcript, you need to generate two pieces of metadata:",
                    "",
                    "1. Name: A concise and descriptive name for the clip",
                    "2. Summary: A short summary of the clip's content",
                    "",
                    "For the name:",
                    "- Think of a hook that will draw users in on social media",
                    "- Create a title that accurately reflects the main topic or theme of the clip",
                    "- Keep it concise but descriptive",
                    "- Limit it to no more than 20 words",
                    "- Ensure it captures the essence of the conversation",
                    "",
                    "For the summary:",
                    "- Write a single paragraph (less than 500 words)",
                    "- Describe the topics of discussion in the clip",
                    "- Describe the tone of the conversation (e.g., funny, informational, spicy)",
                    '- Avoid generic phrases like "in the clip" or "the hosts talk about"',
                    "- Keep the summary as information-dense as possible",
                    "- Focus solely on summarizing the content, without any additional commentary",
                    "",
                    "Once you have crafted both the name and summary, use the submit_metadata tool to provide this information. The tool requires two parameters:",
                    '1. "name": The clip name you created',
                    '2. "summary": The summary you wrote',
                    "",
                    "To use the tool, format your response like this:",
                    '<function_call>submit_metadata(name="Your clip name here", summary="Your summary here")</function_call>',
                    "",
                    "Remember to follow these instructions precisely. Do not include any additional text or explanations outside of the function call. Your entire response should consist solely of the function call with the name and summary you've created based on the transcript.",
                ]
            ),
        }
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
                name = arguments["name"]
                summary = arguments["summary"]

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
