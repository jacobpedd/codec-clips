import anthropic
from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import User
from web.models import Clip, ClipUserScore, UserFeedFollow, UserTopic

client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    base_url="https://anthropic.hconeai.com/",
    default_headers={
        "Helicone-Auth": f"Bearer {settings.HELICONE_API_KEY}",
        "Helicone-User-Id": "ranker",
        "Helicone-Retry-Enabled": "true",
    },
)


def rank_clips_for_user(user_id: str) -> None:
    user = User.objects.get(id=user_id)

    # Get candidate clips All -> ~1000 clips
    candidate_clips = get_clip_candidates(user)

    # Rank the candidate clips
    ranked_clips = rank_clips(user, candidate_clips)

    print("Top 10 clips:")
    for clip in ranked_clips[:10]:
        print(f"Clip: {clip.name} | Show: {clip.feed_item.feed.name}")

    # ReRank the top ranked clips
    # TODO

    # Save the rankings
    return


def get_clip_candidates(user: User):
    return (
        Clip.objects.exclude(user_views__user=user)
        .select_related("feed_item__feed")
        .order_by("-created_at")[:1000]
    )


def rank_clips(user: User, clips: [Clip]):
    user_prompt = user_rank_prompt(user)

    clip_user_scores_to_create = []
    for clip in clips:
        clip_prompt = clip_rank_prompt(clip)
        completion = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            system="\n".join(
                [
                    "You are a helpful assistant that scores clips for a recommendation system.",
                    "You are an expert recommendation system.",
                    "The user will send you a message with two sections:",
                    "# User",
                    "This section contains the profile of the user that is being recommended.",
                    "Following is the list of shows the user follows with their name and descriptions. ",
                    "Interests are the topics they marked interested in.",
                    "Uninterested are the topics they marked not interested in. ",
                    "# Clip",
                    "This section contains information about the clip that is being scored. ",
                    "Podcasts contains info about the podcast the clip is from. ",
                    "Details has information about the clip itself.",
                    "# Your Task",
                    "Your task is to output a single integer score between 1-100.",
                    "The score is your estimate for what percentage of the clip the user will watch.  ",
                    "You should only output the score integer.",
                    "Do not output any other text.",
                ]
            ),
            messages=[
                {"role": "user", "content": "\n".join([user_prompt, clip_prompt])},
            ],
        )

        if not completion:
            raise ValueError("Empty response from model")

        text = completion.content[0].text
        try:
            score = int(text)
        except ValueError:
            raise ValueError("Model outputted invalid score: %s", text)

        clip_user_scores_to_create.append(
            ClipUserScore(user=user, clip=clip, score=score)
        )

    # Use atomic transaction to bulk create all ClipUserScore objects at once
    with transaction.atomic():
        ClipUserScore.objects.bulk_create(
            clip_user_scores_to_create,
            update_conflicts=True,
            unique_fields=["user", "clip"],
            update_fields=["score"],
        )

    # Sort clips by score
    return sorted(
        clips,
        key=lambda clip: next(
            (cus.score for cus in clip_user_scores_to_create if cus.clip == clip), 0
        ),
        reverse=True,
    )


def user_rank_prompt(user: User):
    followed_feeds = UserFeedFollow.objects.filter(user=user).select_related("feed")
    interests = UserTopic.objects.filter(user=user)
    interested_topics = interests.filter(is_interested=True)
    not_interested_topics = interests.filter(is_interested=False)

    prompt = "\n".join(
        [
            "# User",
            "## Following",
            (
                "\n".join(
                    [
                        f"{follows.feed.name}: {follows.feed.description}"
                        for follows in followed_feeds
                    ]
                )
                if followed_feeds.count() > 0
                else "None"
            ),
            "## Interests",
            (
                "\n".join([f"{topic.text}" for topic in interested_topics])
                if interested_topics.count() > 0
                else "None"
            ),
            "## Uninterested",
            (
                "\n".join([f"{topic.text}" for topic in not_interested_topics])
                if not_interested_topics.count() > 0
                else "None"
            ),
        ]
    )
    return prompt


def clip_rank_prompt(clip: Clip):
    duration = (clip.end_time - clip.start_time) / 1000.0
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    return "\n".join(
        [
            "# Clip",
            "## Podcast",
            "Name: " + clip.feed_item.feed.name,
            "Description: " + clip.feed_item.feed.description,
            "Episode Name: " + clip.feed_item.name,
            "## Details",
            "Name: " + clip.name,
            "Summary: " + clip.summary,
            "Duration: " + str(minutes) + " mins " + str(seconds) + " secs",
        ]
    )
