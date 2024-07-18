from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from web.lib.ranker import rank_feeds_for_user
from .models import FeedItem, FeedUserInterest
from .tasks import generate_clips_from_feed_item


@receiver(post_save, sender=FeedItem)
def trigger_clip_generation(sender, instance, created, **kwargs):
    if created:
        generate_clips_from_feed_item.delay(instance.id)


@receiver(post_save, sender=FeedUserInterest)
@receiver(post_delete, sender=FeedUserInterest)
def trigger_feed_following(sender, instance, **kwargs):
    rank_feeds_for_user(instance.user_id)
