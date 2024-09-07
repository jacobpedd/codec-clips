from langsmith import traceable
from pgvector.django import CosineDistance

from web.lib.embed import get_embedding
from web.models import Category, Clip, Topic
from .generate_topics import TopicContent, generate_topics
from .assign_topics import assign_topics
from .assign_categories import assign_categories


@traceable
def clip_tagger(clip: Clip, nearest_neighbors: int = 40):
    # Assign categories to the clip
    categories = Category.objects.all()
    _, assigned_categories = assign_categories(clip, categories)

    # Generate topics using LLM
    generated_topics = generate_topics(clip)

    # Calculate embeddings for generated topics
    topic_embeddings = [generate_topic_embedding(topic) for topic in generated_topics]
    avg_embedding = [sum(e) / len(e) for e in zip(*topic_embeddings)]

    # Find the nearest topics using cosine similarity
    nearest_topics = Topic.objects.annotate(
        similarity=CosineDistance("embedding", avg_embedding)
    ).order_by("similarity")[:nearest_neighbors]

    # Evaluate topics
    evaluations = assign_topics(clip, nearest_topics)

    primary_topics = []
    mentioned_topics = []
    for evaluation in evaluations:
        topic = evaluation["topic"]
        similarity_score = 1 - next(
            t.similarity for t in nearest_topics if t.id == topic.id
        )
        if evaluation["is_mentioned"]:
            if evaluation["is_primary"]:
                primary_topics.append((topic, similarity_score))
            else:
                mentioned_topics.append((topic, similarity_score))

    return assigned_categories, primary_topics, mentioned_topics


def generate_topic_embedding(topic: TopicContent):
    combined_text = f"{topic.name} {' '.join(topic.keywords)} {topic.description}"
    return get_embedding(combined_text)
