from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FeedItem
from .tasks import generate_clips_from_feed_item


@receiver(post_save, sender=FeedItem)
def trigger_clip_generation(sender, instance, created, **kwargs):
    if created:
        generate_clips_from_feed_item.delay(instance.id)
