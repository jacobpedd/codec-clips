from django.contrib.auth.models import User
from celery import shared_task
from web.lib.ranker import rank_clips, get_clip_candidates


@shared_task
def rank_clips_for_user(user_id: str) -> None:
    user = User.objects.get(id=user_id)

    # Get candidate clips All -> ~1000 clips
    candidate_clips = get_clip_candidates(user)

    # Rank the candidate clips
    ranked_clips = rank_clips(user, candidate_clips)

    print("Top 10 clips:")
    for clip in ranked_clips[:10]:
        print(f"Clip: {clip.name} | Show: {clip.feed_item.feed.name}")

    # ReRank the top ranked clips with LLM
    # TODO

    # Manually insert some low score clips to explore
    # TODO
