from typing import List

from langsmith import traceable
from pydantic import BaseModel
from web.lib.llm_client import llm_client
from web.lib.clipper.transcript_utils import get_clip_transcript_text
from web.models import Clip


class TopicContent(BaseModel):
    name: str
    keywords: List[str]
    description: str


class TopicList(BaseModel):
    parent_topics: List[TopicContent]
    topics: List[TopicContent]
    mentioned_topics: List[TopicContent]


@traceable
def generate_topics(clip: Clip) -> List[TopicContent]:
    clip_text = get_clip_transcript_text(clip)
    prompt = f"""<transcript>
{clip_text}
</transcript>

<clip_info>
<name>{clip.name}</name>
<summary>{clip.summary}</summary>
</clip_info>

<instructions>
Generate relevant topics for the above podcast clip. Provide topics in three separate lists: parent topics, topics, and mentioned topics. For each topic, provide a name, keywords, and a description. Follow these guidelines:

1. Analyze the transcript and identify key themes or concepts discussed.
2. Generate the following types of topics:
   - Parent topics (3-5): Broad, overarching themes for podcast classification (e.g., "Arts & Entertainment", "Science & Technology", "Society & Culture")
   - Topics (5-10): More specific categories for podcast classification (e.g., "Stand-up Comedy", "Artificial Intelligence", "Pop Culture")
   - Mentioned topics (5-10): Specific concepts, ideas, or themes mentioned or discussed in the clip (e.g., "Comedy Club Formats", "Audience Interaction", "Comedic Styles")

3. For each topic:
   - Name: Create a concise topic name, typically 1-3 words.
   - Keywords: Provide 3-5 key terms or phrases related to the topic.
   - Description: Write a concise description in one sentence (10-15 words).

4. Ensure a clear distinction between parent topics/topics (for podcast classification) and mentioned topics (content of the clip).
5. Parent topics should be broader and more general than topics.
6. Avoid using specific names, places, or organizations in the topic names.
7. Avoid using articles (a, an, the) at the beginning of topic names.
</instructions>

Now, provide the three separate lists of topics with their names, keywords, and descriptions for this transcript:"""

    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that generates detailed topics for podcast transcripts.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        response_format=TopicList,
    )

    # Combine all topics into a single list
    all_topics = (
        completion.choices[0].message.parsed.parent_topics
        + completion.choices[0].message.parsed.topics
        + completion.choices[0].message.parsed.mentioned_topics
    )

    return all_topics
