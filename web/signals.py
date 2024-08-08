from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import FeedItem, ClipUserView, Feed, Clip
from .tasks import generate_clips_from_feed_item
from .lib.logsnag import logsnag_log, logsnag_insight

# ===================================
# Kick off celery jobs
# ===================================


@receiver(post_save, sender=FeedItem)
def trigger_clip_generation(sender, instance, created, **kwargs):
    if created:
        generate_clips_from_feed_item.delay(instance.id)


# ===================================
# LogSnag event signals
# ===================================


@receiver(post_save, sender=User)
def log_new_user(sender, instance, created, **kwargs):
    if created:
        print(f"New user registered: {instance.username}")

        try:
            logsnag_log(
                event="New User Registered",
                description=f"{instance.username} ({instance.email}) registered",
                icon="👤",
                channel="users",
                notify=True,
                user_id=instance.user.username,
            )
        except Exception as e:
            print(f"Error sending event to LogSnag: {e}")


@receiver(post_save, sender=ClipUserView)
def log_new_session(sender, instance, created, **kwargs):
    if created:
        last_view = (
            ClipUserView.objects.filter(user=instance.user)
            .exclude(id=instance.id)
            .order_by("-created_at")
            .first()
        )

        if (
            not last_view
            or (instance.created_at - last_view.created_at).total_seconds() > 1800
        ):  # 1800 seconds = 30 minutes
            print(f"New session started for user: {instance.user.username}")

            if "test" in instance.user.username or instance.user.is_superuser:
                return

            try:
                logsnag_log(
                    event="New Session Started",
                    description=f"{instance.user.username} started a new session",
                    icon="🎧",
                    channel="users",
                    notify=True,
                    user_id=instance.user.username,
                )
            except Exception as e:
                print(f"Error sending event to LogSnag: {e}")


@receiver(post_save, sender=Feed)
def log_new_feed(sender, instance, created, **kwargs):
    if created:
        try:
            logsnag_log(
                event="New Podcast Feed Added",
                description=f"New podcast feed added: {instance.name}",
                icon="🎙️",
                channel="content",
            )
        except Exception as e:
            print(f"Error sending event to LogSnag: {e}")


@receiver(post_save, sender=FeedItem)
def log_new_feed_item(sender, instance, created, **kwargs):
    if created:
        try:
            logsnag_log(
                event="New Podcast Episode Added",
                description=f"New podcast episode added: {instance.name}",
                icon="🎧",
                channel="content",
            )
        except Exception as e:
            print(f"Error sending event to LogSnag: {e}")


@receiver(post_save, sender=Clip)
def log_new_clip(sender, instance, created, **kwargs):
    if created:
        try:
            logsnag_log(
                event="New Podcast Clip Created",
                description=f"New podcast clip created: {instance.name}",
                icon="✂️",
                channel="content",
            )
        except Exception as e:
            print(f"Error sending event to LogSnag: {e}")


# ===================================
# LogSnag insight signals
# ===================================


@receiver(post_save, sender=User)
@receiver(post_delete, sender=User)
def update_user_insights(sender, instance, **kwargs):
    try:
        total_users = User.objects.count()
        logsnag_insight("Total Users", total_users, "👥")
    except Exception as e:
        print(f"Error sending insight to LogSnag: {e}")


@receiver(post_save, sender=Feed)
@receiver(post_delete, sender=Feed)
def update_feed_insights(sender, instance, **kwargs):
    try:
        total_feeds = Feed.objects.count()
        logsnag_insight("Total Podcasts", total_feeds, "🎙️")
    except Exception as e:
        print(f"Error sending insight to LogSnag: {e}")


@receiver(post_save, sender=FeedItem)
@receiver(post_delete, sender=FeedItem)
def update_feed_item_insights(sender, instance, **kwargs):
    try:
        total_feed_items = FeedItem.objects.count()
        logsnag_insight("Total Episodes", total_feed_items, "🎧")
    except Exception as e:
        print(f"Error sending insight to LogSnag: {e}")


@receiver(post_save, sender=Clip)
@receiver(post_delete, sender=Clip)
def update_clip_insights(sender, instance, **kwargs):
    try:
        total_clips = Clip.objects.count()
        logsnag_insight("Total Clips", total_clips, "✂️")
    except Exception as e:
        print(f"Error sending insight to LogSnag: {e}")
    logsnag_insight("Total Clips", total_clips, "✂️")
