from rest_framework import serializers
from web.models import (
    Category,
    Clip,
    ClipCategoryScore,
    ClipUserView,
    FeedItem,
    Feed,
    FeedUserInterest,
    UserCategoryScore,
)


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


class CategorySerializer(serializers.ModelSerializer):
    clip_count = serializers.SerializerMethodField(read_only=True)
    user_friendly_name = serializers.SerializerMethodField(read_only=True)
    user_friendly_parent_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "parent",
            "user_friendly_name",
            "user_friendly_parent_name",
            "should_display",
            "clip_count",
        ]

    def get_clip_count(self, obj):
        return getattr(obj, "clip_count", None)

    # These are for backwards compatibility
    def get_user_friendly_name(self, obj):
        return obj.name

    def get_user_friendly_parent_name(self, obj):
        return obj.parent.name if obj.parent else None


class ClipCategoryScoreSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = ClipCategoryScore
        fields = ["id", "category", "score"]


class UserCategoryScoreSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = UserCategoryScore
        fields = ["id", "user", "category", "score", "created_at", "updated_at"]
        read_only_fields = ["user", "created_at", "updated_at"]


class ClipSerializer(TimestampedSerializer):
    feed_item = FeedItemSerializer()
    categories = serializers.SerializerMethodField()

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
            "categories",
            "created_at",
            "updated_at",
        ]

    def get_categories(self, obj):
        categories = obj.clipcategoryscore_set.order_by("-score")
        return ClipCategoryScoreSerializer(categories, many=True).data


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
