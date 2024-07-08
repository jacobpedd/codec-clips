from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django import forms
from django.db import transaction

from django.contrib.auth.models import User

from web.tasks import crawl_feed, generate_clips_from_feed_item
from .models import (
    Feed,
    FeedItem,
    Clip,
    ClipUserScore,
    ClipUserView,
    UserFeedFollow,
    UserTopic,
    ClipTopic,
)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_url",
        "get_feed_items_count",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "url")
    actions = ["crawl_selected_feeds"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _feed_items_count=Count("items", distinct=True),
        )
        return queryset

    def get_url(self, obj):
        truncated_url = obj.url[:50] + "..." if len(obj.url) > 50 else obj.url
        return format_html(
            '<a href="{}" target="_blank">RSS</a>', obj.url, truncated_url
        )

    def get_feed_items_count(self, obj):
        count = obj._feed_items_count
        url = reverse("admin:web_feeditem_changelist") + f"?feed__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)

    get_url.short_description = "URL"
    get_url.admin_order_field = "url"

    get_feed_items_count.short_description = "Items"
    get_feed_items_count.admin_order_field = "_feed_items_count"

    def crawl_selected_feeds(self, request, queryset):
        for feed in queryset:
            crawl_feed.delay(feed.id)
        self.message_user(
            request, f"crawl task initiated for {queryset.count()} feeds."
        )

    crawl_selected_feeds.short_description = "crawl selected feeds"


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_feed_name",
        "get_duration",
        "get_audio_url",
        "get_transcript_url",
        "get_clips_count",
        "posted_at",
        "created_at",
    )
    list_filter = ("feed", "posted_at")
    search_fields = ("name", "body", "feed__name")

    actions = ["delete_and_regenerate_clips"]

    @admin.action(description="Regenerate clips for selected items")
    def delete_and_regenerate_clips(self, request, queryset):
        for feed_item in queryset:
            try:
                with transaction.atomic():
                    # Delete existing clips
                    clips_count = feed_item.clips.count()
                    feed_item.clips.all().delete()

                    # Queue task to regenerate clips
                    generate_clips_from_feed_item.delay(feed_item.id)

                self.message_user(
                    request,
                    f"Deleted {clips_count} clips for '{feed_item.name}' and queued clip regeneration.",
                    messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error processing '{feed_item.name}': {str(e)}",
                    messages.ERROR,
                )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _clips_count=Count("clips", distinct=True),
        )
        return queryset

    def get_feed_name(self, obj):
        return obj.feed.name

    def get_duration(self, obj):
        if obj.duration:
            return duration_string(obj.duration)
        return "N/A"

    def get_audio_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{obj.audio_bucket_key}"
        return format_html('<a href="{}" target="_blank">Bucket</a>', url)

    def get_transcript_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{obj.transcript_bucket_key}"
        return format_html('<a href="{}" target="_blank">Bucket</a>', url)

    def get_clips_count(self, obj):
        count = obj._clips_count
        url = reverse("admin:web_clip_changelist") + f"?feed_item__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)

    get_feed_name.admin_order_field = "feed"
    get_feed_name.short_description = "Feed"

    get_duration.short_description = "Duration"

    get_audio_url.short_description = "Audio"
    get_transcript_url.short_description = "Transcript"
    get_clips_count.admin_order_field = "_clips_count"
    get_clips_count.short_description = "Clips"


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
        return duration_string((obj.end_time - obj.start_time) / 1000.0)

    def get_audio_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{obj.audio_bucket_key}"
        return format_html('<a href="{}" target="_blank">Bucket</a>', url)

    get_feed_item_name.admin_order_field = "feed_item__name"
    get_feed_item_name.short_description = "Feed Item Name"

    get_duration.short_description = "Duration"

    get_audio_url.short_description = "Audio"


@admin.register(ClipUserScore)
class ClipUserScoreAdmin(admin.ModelAdmin):
    list_display = ("clip", "user", "score", "created_at", "updated_at")
    list_filter = ("score", "created_at")
    search_fields = ("user__username", "clip__name")


@admin.register(ClipUserView)
class ClipUserViewAdmin(admin.ModelAdmin):
    list_display = ("clip", "user", "duration", "processed", "created_at", "updated_at")
    list_filter = ("created_at", "processed")
    search_fields = ("user__username", "clip__name")


@admin.register(UserFeedFollow)
class UserFeedFollowAdmin(admin.ModelAdmin):
    list_display = ("user", "get_feed_name", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "feed__name")
    autocomplete_fields = ("user", "feed")

    def get_feed_name(self, obj):
        return obj.feed.name

    get_feed_name.short_description = "Feed"
    get_feed_name.admin_order_field = "feed__name"


@admin.register(UserTopic)
class UserTopicAdmin(admin.ModelAdmin):
    list_display = ("user", "text", "is_interested", "created_at")
    list_filter = ("is_interested", "created_at")
    search_fields = ("user__username", "text")
    autocomplete_fields = ("user",)


@admin.register(ClipTopic)
class ClipTopicAdmin(admin.ModelAdmin):
    list_display = ("clip", "text", "created_at")
    list_filter = ("created_at",)
    search_fields = ("clip__name", "text")
    autocomplete_fields = ("clip",)


def duration_string(duration):
    hours = int(duration // 3600)
    minutes = int(duration % 3600 // 60)
    seconds = int(duration % 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"
