from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from pgvector.django import VectorField

def default_vector():
    # 768 is from nomic-embed-text-v1.5-Q in embed.py
    return [0.0] * 768

class Feed(models.Model):
    url = models.URLField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    total_itunes_ratings = models.IntegerField(default=0)
    popularity_percentile = models.FloatField(default=0.0)
    topic_embedding = VectorField(dimensions=768, default=default_vector)
    language = models.CharField(max_length=100)
    is_english = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FeedItem(models.Model):
    name = models.CharField(max_length=255)
    body = models.TextField()
    audio_url = models.URLField(max_length=2000, unique=True)
    audio_bucket_key = models.CharField(max_length=2000)
    transcript_bucket_key = models.CharField(max_length=2000)
    duration = models.IntegerField()
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="items")

    def __str__(self):
        return self.name
    
class FeedTopic(models.Model):
    text = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="topics")

    class Meta:
        unique_together = ("feed", "text")

    def __str__(self):
        return self.text


class Clip(models.Model):
    name = models.CharField(max_length=2000)
    body = models.TextField()
    summary = models.TextField()
    start_time = models.IntegerField()
    end_time = models.IntegerField()
    audio_bucket_key = models.CharField(max_length=2000)
    transcript_embedding = VectorField(dimensions=768, default=default_vector)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed_item = models.ForeignKey(
        FeedItem, on_delete=models.CASCADE, related_name="clips"
    )

    def __str__(self):
        return self.name


class ClipUserView(models.Model):
    duration = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="user_views")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_clip_views"
    )

    class Meta:
        unique_together = ("clip", "user")

    def __str__(self):
        return (
            f"{self.user.username} viewed {self.clip.name} for {self.duration} seconds"
        )
    

class FeedUserInterest(models.Model):
    is_interested = models.BooleanField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="feed_follows"
    )
    feed = models.ForeignKey(
        Feed, on_delete=models.CASCADE, related_name="user_follows"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "feed")

    def __str__(self):
        return f"{self.user.username} {"follows" if self.is_interested else "blocks"} {self.feed.name}"
