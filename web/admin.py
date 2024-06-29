from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Feed,
    FeedItem,
    Clip,
    ClipScore,
    ClipUserScore,
    ClipUserView,
)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ("name", "get_url", "created_at", "updated_at")
    search_fields = ("name", "url")

    def get_url(self, obj):
        truncated_url = obj.url[:50] + "..." if len(obj.url) > 50 else obj.url
        return format_html(
            '<a href="{}" target="_blank">{}</a>', obj.url, truncated_url
        )

    get_url.short_description = "URL"
    get_url.admin_order_field = "url"


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_feed_name",
        "duration",
        "get_audio_url",
        "posted_at",
        "created_at",
    )
    list_filter = ("feed", "posted_at")
    search_fields = ("name", "body", "feed__name")

    def get_feed_name(self, obj):
        return obj.feed.name

    def get_audio_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{obj.audio_bucket_key}"
        truncated_url = url[:50] + "..." if len(url) > 50 else url
        return format_html('<a href="{}" target="_blank">{}</a>', url, truncated_url)

    get_feed_name.admin_order_field = "feed__name"
    get_feed_name.short_description = "Feed Name"

    get_audio_url.short_description = "Audio URL"


@admin.register(Clip)
class ClipAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_feed_item_name",
        "get_duration",
        "get_audio_url",
        "created_at",
    )
    list_filter = ("feed_item", "created_at")
    search_fields = ("name", "body")

    def get_feed_item_name(self, obj):
        return obj.feed_item.name

    def get_duration(self, obj):
        start_seconds = obj.start_time / 1000.0
        end_seconds = obj.end_time / 1000.0
        duration = end_seconds - start_seconds

        # Display duration in minutes and seconds
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"

    def get_audio_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{obj.audio_bucket_key}"
        truncated_url = url[:50] + "..." if len(url) > 50 else url
        return format_html('<a href="{}" target="_blank">{}</a>', url, truncated_url)

    get_feed_item_name.admin_order_field = "feed_item__name"
    get_feed_item_name.short_description = "Feed Item Name"

    get_duration.short_description = "Duration"

    get_audio_url.short_description = "Audio URL"


@admin.register(ClipScore)
class ClipScoreAdmin(admin.ModelAdmin):
    list_display = ("clip", "score", "created_at")
    list_filter = ("score", "created_at")


@admin.register(ClipUserScore)
class ClipUserScoreAdmin(admin.ModelAdmin):
    list_display = ("clip", "user", "score", "created_at")
    list_filter = ("score", "created_at")
    search_fields = ("user__username", "clip__name")


@admin.register(ClipUserView)
class ClipUserViewAdmin(admin.ModelAdmin):
    list_display = ("clip", "user", "duration", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "clip__name")
