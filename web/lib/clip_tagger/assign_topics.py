from typing import Dict, List
from langsmith import traceable
from pydantic import BaseModel, Field
from web.lib.llm_client import llm_client
from web.lib.clipper.transcript_utils import get_clip_transcript_text
from web.models import Clip, Topic
from enum import Enum


def create_topic_enum(topics: List[Topic]):
    return Enum("TopicEnum", {topic.name: topic.name for topic in topics})


@traceable
def assign_topics(clip: Clip, topics: List[Topic]) -> List[Dict]:
    clip_text = get_clip_transcript_text(clip)
    clip_info = f"<name>{clip.name}</name>\n<summary>{clip.summary}</summary>"

    TopicEnum = create_topic_enum(topics)

    class DynamicTopicMention(BaseModel):
        name: TopicEnum
        is_primary: bool

    class DynamicTopicEvaluation(BaseModel):
        explanation: str
        topic_mentions: List[DynamicTopicMention] = Field(
            ..., description="List of topic mentions"
        )

    topics_info = "\n".join([f"{topic.name}: {topic.description}" for topic in topics])

    prompt = f"""<transcript>
{clip_text}
</transcript>

<clip_info>
{clip_info}
</clip_info>

<topics_to_evaluate>
{topics_info}
</topics_to_evaluate>

<instructions>
Evaluate the podcast clip and determine which topics are relevant. Your response should follow this structure:

1. Explanation: Provide a brief explanation of your evaluation, focusing on the overall content and how the chosen topics represent the clip.

2. Topic Mentions: Create a list of 5-20 relevant topics. For each relevant topic:
   - name: Use the exact topic name from the list provided.
   - is_primary: Set to true only if it's a main focus of the clip and would fit as a category in a podcast player. Otherwise, set to false.

Only include topics that are actually mentioned or relevant to the clip. Aim for a minimum of 5 topics and a maximum of 20 topics. If there are fewer than 10 relevant topics, include the most loosely related ones to reach the minimum. If there are more than 20 relevant topics, prioritize the most significant ones.

Consider how a listener would search for this clip in a podcast player and what categories would be most useful for discovery and organization.
</instructions>"""

    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that categorizes podcast clips into relevant topic categories.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format=DynamicTopicEvaluation,
    )

    results = completion.choices[0].message.parsed
    evaluations = []
    for topic_mention in results.topic_mentions:
        topic = next(t for t in topics if t.name == topic_mention.name.value)
        evaluation = {
            "topic": topic,
            "explanation": results.explanation,
            "is_mentioned": True,  # If it's in the list, it's mentioned
            "is_primary": topic_mention.is_primary,
        }
        evaluations.append(evaluation)

    return evaluations
