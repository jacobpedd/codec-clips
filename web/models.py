from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Feed(models.Model):
    url = models.URLField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    total_itunes_ratings = models.IntegerField(default=0)
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


class Clip(models.Model):
    name = models.CharField(max_length=2000)
    body = models.TextField()
    summary = models.TextField()
    start_time = models.IntegerField()
    end_time = models.IntegerField()
    audio_bucket_key = models.CharField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed_item = models.ForeignKey(
        FeedItem, on_delete=models.CASCADE, related_name="clips"
    )

    def __str__(self):
        return self.name


class ClipUserScore(models.Model):
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="user_scores")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_clip_scores"
    )

    class Meta:
        unique_together = ("clip", "user")

    def __str__(self):
        return f"{self.user.username} rated {self.clip.name} with score {self.score}"


class ClipUserView(models.Model):
    duration = models.IntegerField()
    processed = models.BooleanField(default=False)
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
    

class FeedUserScore(models.Model):
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="feed_scores"
    )
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="user_scores")

    class Meta:
        unique_together = ("user", "feed")

    def __str__(self):
        return f"{self.user.username} rated {self.feed.name} with score {self.score}"
