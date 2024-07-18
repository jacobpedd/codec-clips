from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
import numpy as np

def validate_embedding_size(value):
    # 1024 is the size of cohere's embed-english-v3.0 embedding
    if not isinstance(value, list) or len(value) != 1024:
        raise ValidationError('Topic embedding must be a list of 1024 floats.')

def validate_list_of_floats(value):
    if not all(isinstance(item, (int, float)) for item in value):
        raise ValidationError('All items in the list must be numbers.')

def default_topic_embedding():
    return list([0.0] * 1024)

class Feed(models.Model):
    url = models.URLField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    total_itunes_ratings = models.IntegerField(default=0)
    topic_embedding = models.JSONField(
        default=default_topic_embedding,
        validators=[validate_embedding_size, validate_list_of_floats]
    )
    language = models.CharField(max_length=100)
    is_english = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def get_topic_embedding(self):
        """Retrieve the topic embedding as a numpy array."""
        if self.topic_embedding:
            return np.array(self.topic_embedding)
        return None

    def set_topic_embedding(self, embedding):
        """Set the topic embedding from a numpy array or list."""
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        self.topic_embedding = embedding
        self.full_clean()  # This will run the validators

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
