from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Feed(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class FeedItem(models.Model):
    name = models.CharField(max_length=255)
    body = models.TextField()
    audio_url = models.URLField()
    audio_bucket_key = models.CharField(max_length=255)
    duration = models.IntegerField()
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="items")


class Transcript(models.Model):
    text_bucket_key = models.CharField(max_length=255, null=True, blank=True)
    feed_item = models.OneToOneField(
        FeedItem, on_delete=models.CASCADE, related_name="transcript"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Clip(models.Model):
    name = models.CharField(max_length=255)
    body = models.TextField()
    start_time = models.IntegerField()
    end_time = models.IntegerField()
    duration = models.IntegerField()
    audio_bucket_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed_item = models.ForeignKey(
        FeedItem, on_delete=models.CASCADE, related_name="clips"
    )


class ClipScore(models.Model):
    score = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="scores")


class ClipUserScore(models.Model):
    score = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="user_scores")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="clip_user_scores"
    )


class ClipUserView(models.Model):
    duration = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="user_views")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="clip_user_views"
    )
