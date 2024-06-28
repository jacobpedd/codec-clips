from django.contrib import admin
from .models import (
    Feed,
    FeedItem,
    Transcript,
    Clip,
    ClipScore,
    ClipUserScore,
    ClipUserView,
)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "created_at", "updated_at")
    search_fields = ("name", "url")


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = ("name", "feed", "duration", "posted_at", "created_at")
    list_filter = ("feed", "posted_at")
    search_fields = ("name", "body")


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("feed_item", "text_bucket_key", "created_at")
    search_fields = ("feed_item__name", "text_bucket_key")


@admin.register(Clip)
class ClipAdmin(admin.ModelAdmin):
    list_display = ("name", "feed_item", "start_time", "end_time", "duration")
    list_filter = ("feed_item", "created_at")
    search_fields = ("name", "body")


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
