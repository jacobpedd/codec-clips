from typing import List, Tuple
from langsmith import traceable
from pydantic import BaseModel, Field
from web.models import Clip, Category
from web.lib.llm_client import llm_client
from web.lib.clipper.transcript_utils import get_clip_transcript_text
from enum import Enum


def create_category_enum(categories: List[Category]):
    return Enum("CategoryEnum", {cat.name: cat.name for cat in categories})


def create_category_assignment_model(categories: List[Category]):
    CategoryEnum = create_category_enum(categories)

    class DynamicCategoryAssignment(BaseModel):
        explanation: str = Field(
            ..., description="Explanation for the category assignment"
        )
        categories: List[CategoryEnum] = Field(
            ..., description="List of assigned categories"
        )

    return DynamicCategoryAssignment


@traceable
def assign_categories(
    clip: Clip, categories: List[Category]
) -> Tuple[str, List[Category]]:
    clip_text = get_clip_transcript_text(clip)
    clip_info = f"<name>{clip.name}</name>\n<summary>{clip.summary}</summary>"

    # Generate category tree string
    category_tree = "Podcast Categories:\n\n"
    for category in categories:
        if category.parent is None:
            category_tree += f"{category.name}: {category.description}\n"
            for subcategory in category.children.all():
                category_tree += f"- {subcategory.name}: {subcategory.description}\n"
            category_tree += "\n"

    prompt = f"""<transcript>
{clip_text}
</transcript>

<clip_info>
{clip_info}
</clip_info>

<category_tree>
{category_tree}
</category_tree>

<instructions>
Analyze the given podcast clip and determine which categories and subcategories from the provided category tree best represent the overall content and theme of the entire clip. These categories are for a podcast player, so consider how listeners would search for or expect to find this type of content.

Guidelines:
1. Assign categories that reflect the entire clip.
2. Prefer assigning to a single category unless it's clearly necessary to assign to multiple categories.
3. Imagine as a podcast listener, where would you expect to find this content?
4. Don't assign to generic categories like "Society & Culture" unless there's no where else to go.
5. Don't assign topics that are only touched on.

Provide:
1. A brief explanation for your category choices (2-3 sentences), focusing on how the chosen categories represent the clip's overall content.
2. A list of assigned categories and subcategories. Only include categories that truly represent the clip's main focus.

Remember, the goal is to categorize the clip in a way that helps listeners find relevant content in a podcast player, not to list every topic mentioned.
</instructions>"""

    DynamicCategoryAssignment = create_category_assignment_model(categories)

    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that categorizes podcast clips into relevant categories based on their overall content and main themes.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format=DynamicCategoryAssignment,
    )

    result = completion.choices[0].message.parsed

    # Convert category names back to Category objects
    category_dict = {cat.name: cat for cat in categories}
    assigned_categories = [category_dict[cat.value] for cat in result.categories]

    return (result.explanation, assigned_categories)
