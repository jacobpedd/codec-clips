from django.contrib import admin
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
    list_display = ("name", "url", "created_at", "updated_at")
    search_fields = ("name", "url")


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = ("name", "get_feed_name", "duration", "posted_at", "created_at")
    list_filter = ("feed", "posted_at")
    search_fields = ("name", "body", "feed__name")

    def get_feed_name(self, obj):
        return obj.feed.name

    get_feed_name.admin_order_field = "feed__name"
    get_feed_name.short_description = "Feed Name"


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
