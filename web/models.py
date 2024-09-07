from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from pgvector.django import VectorField, HnswIndex
from django.contrib.postgres.fields import ArrayField

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
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    embedding = VectorField(dimensions=768, default=default_vector)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True)
    should_display = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'parent')
        verbose_name_plural = "Categories"

class ClipCategoryScore(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('clip', 'category')

    def __str__(self):
        return f'{self.clip.name} - {self.category.name}: {self.score}'
    

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

class Topic(models.Model):
    name = models.CharField(max_length=255, unique=True)
    keywords = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    embedding = VectorField(dimensions=768, default=default_vector)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def is_descendant_of(self, potential_ancestor):
        """
        Check if this topic is a descendant of the potential_ancestor.
        """
        if self == potential_ancestor:
            return True
        current = self.parent
        while current:
            if current == potential_ancestor:
                return True
            current = current.parent
        return False

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['parent']),
            HnswIndex(
                name='topic_embedding_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
        ]

class ClipTopicScore(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    score = models.FloatField()
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('clip', 'topic')

    def __str__(self):
        return f'{self.clip.name} - {self.topic.name}: {self.score} ({"Primary" if self.is_primary else "Mentioned"})'
