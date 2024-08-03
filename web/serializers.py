from rest_framework import serializers
from web.models import Clip, ClipUserView, FeedItem, Feed, FeedUserInterest


class TimestampedSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class FeedSerializer(TimestampedSerializer):
    class Meta:
        model = Feed
        fields = [
            "id",
            "name",
            "description",
            "url",
            "artwork_bucket_key",
            "created_at",
            "updated_at",
        ]


class FeedItemSerializer(TimestampedSerializer):
    feed = FeedSerializer()

    class Meta:
        model = FeedItem
        fields = ["id", "name", "feed", "posted_at", "created_at", "updated_at"]


class ClipSerializer(TimestampedSerializer):
    feed_item = FeedItemSerializer()

    class Meta:
        model = Clip
        fields = [
            "id",
            "name",
            "body",
            "summary",
            "start_time",
            "end_time",
            "audio_bucket_key",
            "feed_item",
            "created_at",
            "updated_at",
        ]


class ClipUserViewSerializer(TimestampedSerializer):
    class Meta:
        model = ClipUserView
        fields = ["id", "clip", "user", "duration", "created_at", "updated_at"]
        read_only_fields = ["user"]


class HistorySerializer(TimestampedSerializer):
    clip = ClipSerializer()

    class Meta:
        model = ClipUserView
        fields = ["id", "clip", "duration", "created_at", "updated_at"]


class FeedUserInterestSerializer(TimestampedSerializer):
    feed = FeedSerializer(read_only=True)
    feed_id = serializers.PrimaryKeyRelatedField(
        queryset=Feed.objects.all(), write_only=True, source="feed"
    )

    class Meta:
        model = FeedUserInterest
        fields = ["id", "user", "feed", "feed_id", "is_interested", "created_at"]
        read_only_fields = ["user"]
