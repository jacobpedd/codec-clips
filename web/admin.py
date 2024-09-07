from urllib.parse import quote
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, BooleanField, Exists, OuterRef, Q
from django.db.models.functions import Cast
from pgvector.django import L2Distance
from web.tasks.crawler_tasks import recalculate_feed_embedding_and_topics


from django.db import transaction

from web.tasks import crawl_feed, generate_clips_from_feed_item
from .models import (
    Feed,
    FeedItem,
    Clip,
    ClipUserView,
    FeedTopic,
    FeedUserInterest,
    Category,
    ClipCategoryScore,
    UserCategoryScore,
    Topic,
    ClipTopicScore,
)


class HasItemsFilter(SimpleListFilter):
    title = "has items"
    parameter_name = "has_items"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(items__isnull=False).distinct()
        if self.value() == "no":
            return queryset.filter(items__isnull=True)


class FeedHasClipsFilter(SimpleListFilter):
    title = "has clips"
    parameter_name = "has_clips"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        clips_exist = Exists(Clip.objects.filter(feed_item__feed=OuterRef("pk")))
        if self.value() == "yes":
            return queryset.filter(clips_exist)
        if self.value() == "no":
            return queryset.filter(~clips_exist)


class IsEnglishFilter(SimpleListFilter):
    title = "Is English"
    parameter_name = "is_english"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(is_english=True)
        if self.value() == "no":
            return queryset.filter(is_english=False)


class HasZeroEmbeddingFilter(admin.SimpleListFilter):
    title = "Has Zero Embedding"
    parameter_name = "has_zero_embedding"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        zero_vector = [0.0] * 768  # Assuming 768-dimensional embeddings
        if self.value() == "yes":
            return queryset.filter(topic_embedding=zero_vector)
        if self.value() == "no":
            return queryset.exclude(topic_embedding=zero_vector)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "format_total_itunes_ratings",
        "get_url",
        "get_feed_items_count",
        "created_at",
        "updated_at",
        "has_zero_embedding",
    )
    list_filter = (
        "created_at",
        HasItemsFilter,
        FeedHasClipsFilter,
        IsEnglishFilter,
        HasZeroEmbeddingFilter,
    )
    search_fields = ("name", "url")
    actions = [
        "crawl_selected_feeds",
        "set_selected_feeds_is_english",
        "recalculate_selected_feed_embeddings_and_topics",
    ]
    exclude = ("topic_embedding",)  # some pg-vector bug breaks the admin

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        zero_vector = [0.0] * 768  # Assuming 768-dimensional embeddings
        queryset = queryset.annotate(
            _feed_items_count=Count("items", distinct=True),
            _is_zero_embedding=Cast(
                L2Distance("topic_embedding", zero_vector) == 0, BooleanField()
            ),
        )
        return queryset

    def has_zero_embedding(self, obj):
        return obj._is_zero_embedding

    has_zero_embedding.boolean = True
    has_zero_embedding.short_description = "Zero Embedding"
    has_zero_embedding.admin_order_field = "_is_zero_embedding"

    def get_url(self, obj):
        truncated_url = obj.url[:50] + "..." if len(obj.url) > 50 else obj.url
        return format_html(
            '<a href="{}" target="_blank">RSS</a>', obj.url, truncated_url
        )

    get_url.short_description = "URL"
    get_url.admin_order_field = "url"

    def get_feed_items_count(self, obj):
        count = obj._feed_items_count
        url = reverse("admin:web_feeditem_changelist") + f"?feed__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)

    get_feed_items_count.short_description = "Items"
    get_feed_items_count.admin_order_field = "_feed_items_count"

    def format_total_itunes_ratings(self, obj):
        if obj.total_itunes_ratings is None:
            return "N/A"
        formatted_ratings = "{:,}".format(obj.total_itunes_ratings)
        return f"{formatted_ratings}"

    format_total_itunes_ratings.short_description = "Ratings"
    format_total_itunes_ratings.admin_order_field = "total_itunes_ratings"

    def crawl_selected_feeds(self, request, queryset):
        for feed in queryset:
            crawl_feed.delay(feed.id)
        self.message_user(
            request, f"crawl task initiated for {queryset.count()} feeds."
        )

    def set_selected_feeds_is_english(self, request, queryset):
        for feed in queryset:
            feed.is_english = True
            feed.save()
        self.message_user(
            request, f"set_is_english task initiated for {queryset.count()} feeds."
        )

    def recalculate_selected_feed_embeddings_and_topics(self, request, queryset):
        for feed in queryset:
            recalculate_feed_embedding_and_topics.delay(feed.id)
        self.message_user(
            request,
            f"Recrawling topics and recalculating embeddings for {queryset.count()} feeds.",
        )

    crawl_selected_feeds.short_description = "crawl selected feeds"
    set_selected_feeds_is_english.short_description = "set is_english"


class FeedItemHasClipsFilter(SimpleListFilter):
    title = "has clips"
    parameter_name = "has_clips"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.annotate(clip_count=Count("clips")).filter(clip_count__gt=0)
        if self.value() == "no":
            return queryset.annotate(clip_count=Count("clips")).filter(clip_count=0)


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
    list_filter = ("posted_at", FeedItemHasClipsFilter)
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
        url = f"{settings.R2_BUCKET_URL}/{quote(obj.audio_bucket_key)}"
        return format_html('<a href="{}" target="_blank">Bucket</a>', url)

    def get_transcript_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{quote(obj.transcript_bucket_key)}"
        return format_html('<a href="{}" target="_blank">Bucket</a>', url)

    def get_clips_count(self, obj):
        count = obj._clips_count
        url = reverse("admin:web_clip_changelist") + f"?feed_item__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)

    def has_clips(self, obj):
        return obj._clips_count > 0

    has_clips.boolean = True
    has_clips.short_description = "Has Clips"

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
        "get_category_scores_count",
        "get_topic_scores_count",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("name", "body")
    exclude = ("transcript_embedding",)  # some pg-vector bug breaks the admin

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            category_scores_count=Count("clipcategoryscore", distinct=True),
            topic_scores_count=Count("cliptopicscore", distinct=True),
        )
        return queryset

    @admin.display(
        ordering="category_scores_count", description="Category Scores Count"
    )
    def get_category_scores_count(self, obj):
        url = (
            reverse("admin:web_clipcategoryscore_changelist")
            + f"?clip__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.category_scores_count)

    @admin.display(ordering="topic_scores_count", description="Topic Scores Count")
    def get_topic_scores_count(self, obj):
        url = (
            reverse("admin:web_cliptopicscore_changelist")
            + f"?clip__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.topic_scores_count)

    def get_feed_item_name(self, obj):
        return obj.feed_item.name

    def get_duration(self, obj):
        return duration_string((obj.end_time - obj.start_time) / 1000.0)

    def get_audio_url(self, obj):
        url = f"{settings.R2_BUCKET_URL}/{quote(obj.audio_bucket_key)}"
        return format_html('<a href="{}" target="_blank">Bucket</a>', url)

    get_feed_item_name.admin_order_field = "feed_item__name"
    get_feed_item_name.short_description = "Feed Item Name"

    get_duration.short_description = "Duration"

    get_audio_url.short_description = "Audio"


class UserFilter(admin.SimpleListFilter):
    title = "User"
    parameter_name = "user"

    def lookups(self, request, model_admin):
        users = (
            get_user_model()
            .objects.filter(
                id__in=model_admin.get_queryset(request).values_list("user", flat=True)
            )
            .order_by("username")
        )
        return [(user.id, user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__id=self.value())
        return queryset


@admin.register(ClipUserView)
class ClipUserViewAdmin(admin.ModelAdmin):
    list_display = ("clip", "user", "duration", "created_at", "updated_at")
    list_filter = ("created_at", UserFilter)
    search_fields = ("user__username", "clip__name")


@admin.register(FeedUserInterest)
class FeedUserInterestAdmin(admin.ModelAdmin):
    list_display = ("user", "get_feed_name", "is_interested", "created_at")
    list_filter = ("created_at", UserFilter)
    search_fields = ("user__username", "feed__name")
    autocomplete_fields = ("user", "feed")

    def get_feed_name(self, obj):
        return obj.feed.name

    get_feed_name.short_description = "Feed"
    get_feed_name.admin_order_field = "feed__name"


def duration_string(duration):
    hours = int(duration // 3600)
    minutes = int(duration % 3600 // 60)
    seconds = int(duration % 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


@admin.register(FeedTopic)
class FeedTopicAdmin(admin.ModelAdmin):
    list_display = ("text", "get_feed_name", "created_at", "updated_at")
    list_filter = ("feed", "created_at")
    search_fields = ("text", "feed__name")

    def get_feed_name(self, obj):
        return obj.feed.name

    get_feed_name.admin_order_field = "feed__name"
    get_feed_name.short_description = "Feed"


class HasParentFilter(admin.SimpleListFilter):
    title = "Has Parent"
    parameter_name = "has_parent"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(parent__isnull=False)
        if self.value() == "no":
            return queryset.filter(parent__isnull=True)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "parent_link",
        "description",
        "get_clip_count",
        "should_display",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at", HasParentFilter, "should_display")
    search_fields = ("name", "description", "parent__name")
    exclude = ("embedding",)
    actions = ["set_should_display_true", "set_should_display_false"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            clip_count=Count("clipcategoryscore", distinct=True)
        )
        return queryset

    def parent_link(self, obj):
        if obj.parent:
            url = reverse("admin:web_category_change", args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.name)
        return "-"

    parent_link.short_description = "Parent"
    parent_link.admin_order_field = "parent__name"

    def get_clip_count(self, obj):
        url = (
            reverse("admin:web_clipcategoryscore_changelist")
            + f"?category__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.clip_count)

    get_clip_count.short_description = "Clips"
    get_clip_count.admin_order_field = "clip_count"

    @admin.action(description="Set selected categories to display")
    def set_should_display_true(self, request, queryset):
        updated = queryset.update(should_display=True)
        self.message_user(request, f"{updated} categories were set to display.")

    @admin.action(description="Set selected categories to not display")
    def set_should_display_false(self, request, queryset):
        updated = queryset.update(should_display=False)
        self.message_user(request, f"{updated} categories were set to not display.")


@admin.register(ClipCategoryScore)
class ClipCategoryScoreAdmin(admin.ModelAdmin):
    list_display = ("clip", "category", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("clip__name", "category__name")


@admin.register(UserCategoryScore)
class UserCategoryScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "category__name")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_parent_name",
        "get_keywords",
        "get_description_preview",
        "primary_clip_count",
        "non_primary_clip_count",
        "total_clip_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at", HasParentFilter)
    search_fields = (
        "name",
        "keywords",
        "description",
        "parent__name",
    )
    exclude = ("embedding",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            primary_clips=Count(
                "cliptopicscore", filter=Q(cliptopicscore__is_primary=True)
            ),
            non_primary_clips=Count(
                "cliptopicscore", filter=Q(cliptopicscore__is_primary=False)
            ),
            total_clips=Count("cliptopicscore"),
        )
        return queryset

    def get_parent_name(self, obj):
        if obj.parent:
            url = reverse("admin:web_topic_change", args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.name)
        return "-"

    get_parent_name.short_description = "Parent Topic"
    get_parent_name.admin_order_field = "parent__name"

    def primary_clip_count(self, obj):
        url = (
            reverse("admin:web_cliptopicscore_changelist")
            + f"?topic__id__exact={obj.id}&is_primary__exact=1"
        )
        return format_html('<a href="{}">{}</a>', url, obj.primary_clips)

    primary_clip_count.admin_order_field = "primary_clips"
    primary_clip_count.short_description = "Primary Clips"

    def non_primary_clip_count(self, obj):
        url = (
            reverse("admin:web_cliptopicscore_changelist")
            + f"?topic__id__exact={obj.id}&is_primary__exact=0"
        )
        return format_html('<a href="{}">{}</a>', url, obj.non_primary_clips)

    non_primary_clip_count.admin_order_field = "non_primary_clips"
    non_primary_clip_count.short_description = "Non-Primary Clips"

    def total_clip_count(self, obj):
        url = (
            reverse("admin:web_cliptopicscore_changelist")
            + f"?topic__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.total_clips)

    total_clip_count.admin_order_field = "total_clips"
    total_clip_count.short_description = "Total Clips"

    def get_keywords(self, obj):
        if obj.keywords:
            return ", ".join(obj.keywords[:5]) + (
                "..." if len(obj.keywords) > 5 else ""
            )
        return "No keywords"

    get_keywords.short_description = "Keywords"

    def get_description_preview(self, obj):
        if obj.description:
            return (
                obj.description[:100] + "..."
                if len(obj.description) > 100
                else obj.description
            )
        return "No description"

    get_description_preview.short_description = "Description Preview"


@admin.register(ClipTopicScore)
class ClipTopicScoreAdmin(admin.ModelAdmin):
    list_display = ("clip", "topic", "score", "is_primary", "created_at")
    list_filter = ("created_at", "is_primary")
    search_fields = ("clip__name", "topic__name")
