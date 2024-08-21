from django.db import models, connection
from django.utils import timezone
from django.contrib.auth.models import User
from pgvector.django import VectorField, HnswIndex

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
    artwork_bucket_key = models.CharField(max_length=2000)
    language = models.CharField(max_length=100)
    is_english = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['total_itunes_ratings']),
            models.Index(fields=['is_english']),
            models.Index(fields=['popularity_percentile']),
            models.Index(fields=['is_english', 'popularity_percentile']),
            HnswIndex(
                name='feed_topic_embedding_idx',
                fields=['topic_embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
        ]

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

    class Meta:
        indexes = [
            models.Index(fields=['posted_at']),
            models.Index(fields=['feed']),
            models.Index(fields=['feed', 'posted_at']),
        ]

    def __str__(self):
        return self.name

class FeedTopic(models.Model):
    text = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="topics")

    class Meta:
        unique_together = ("feed", "text")
        indexes = [
            models.Index(fields=['feed', 'text']),
        ]

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

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['feed_item']),
            models.Index(fields=['feed_item', 'created_at']),
            models.Index(fields=['feed_item', 'created_at', 'name', 'summary']),
            HnswIndex(
                name='clip_transcript_embedding_idx',
                fields=['transcript_embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
        ]

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
        indexes = [
            models.Index(fields=['clip']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'clip', 'created_at']),
        ]

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
        indexes = [
            models.Index(fields=['user', 'feed', 'is_interested']),
            models.Index(fields=['feed', 'is_interested']),
        ]

    def __str__(self):
        return f"{self.user.username} {"follows" if self.is_interested else "blocks"} {self.feed.name}"
    

class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', null=True, blank=True)
    user_friendly_name = models.CharField(max_length=255, null=True, blank=True)
    user_friendly_parent_name = models.CharField(max_length=255, null=True, blank=True)
    should_display = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        if self.user_friendly_name:
            return self.user_friendly_name
        else:
            return self.name.replace("/Other", "").split("/")[-1]

    class Meta:
        unique_together = ('name', 'parent')

class ClipCategoryScore(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('clip', 'category')

    def __str__(self):
        return f'{self.clip.name} - {self.category.display_name}: {self.score}'
    

class UserCategoryScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f"{self.user.username} - {self.category.name}: {self.score}"
