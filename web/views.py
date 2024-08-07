import random
import re
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.throttling import AnonRateThrottle
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, connection
from django.db.models import (
    Q,
    F,
    Case,
    When,
    Value,
    FloatField,
    Subquery,
    OuterRef,
    Avg,
    ExpressionWrapper,
    Window,
    F,
)
from django.db.models.functions import Extract, RowNumber
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.conf import settings
from django.urls import reverse
from pgvector.django import CosineDistance
from django.contrib.postgres.aggregates import ArrayAgg
from web import serializers
from web.models import (
    Clip,
    ClipUserView,
    FeedTopic,
    FeedUserInterest,
    Feed,
)
import resend


class RecommendedFeedsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.FeedSerializer

    def get_queryset(self):
        user = self.request.user

        # Get average embedding of feeds the user is interested in
        avg_feed_embedding = FeedUserInterest.objects.filter(
            user=user, is_interested=True
        ).aggregate(Avg("feed__topic_embedding"))["feed__topic_embedding__avg"]

        # Get recommended feeds
        recommended_feeds = (
            Feed.objects.filter(is_english=True)
            .exclude(user_follows__user=user)  # Exclude feeds the user already follows
            .exclude(topic_embedding=[0] * 768)
            .annotate(
                similarity=CosineDistance("topic_embedding", avg_feed_embedding),
                score=Case(
                    When(
                        similarity__isnull=False,
                        then=(1 - F("similarity")) + F("popularity_percentile") * 0.2,
                    ),
                    default=F("popularity_percentile"),
                    output_field=FloatField(),
                ),
                topic_texts=Subquery(
                    FeedTopic.objects.filter(feed=OuterRef("pk"))
                    .values("feed")
                    .annotate(topics=ArrayAgg("text"))
                    .values("topics")
                ),
            )
            .order_by("-score")
        )

        return recommended_feeds


class QueueViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ClipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Get exclude_clip_ids from query parameters
        exclude_clip_ids = self.request.query_params.getlist("exclude_clip_ids", [])
        if len(exclude_clip_ids) == 1 and "," in exclude_clip_ids[0]:
            exclude_clip_ids = exclude_clip_ids[0].split(",")

        # Exclude clips from feeds the user has already viewed
        recent_feeds = (
            ClipUserView.objects.filter(user=user)
            .order_by("-created_at")[:10]
            .values_list("clip__feed_item__feed", flat=True)
        )

        if FeedUserInterest.objects.filter(user=user).count() < 3:
            print("Not enough followed feeds for user")
            return []

        # Get average embedding of feeds the user is interested in
        avg_feed_embedding = FeedUserInterest.objects.filter(
            user=user, is_interested=True
        ).aggregate(Avg("feed__topic_embedding"))["feed__topic_embedding__avg"]

        # Get blocked feeds
        blocked_feeds = FeedUserInterest.objects.filter(
            user=user, is_interested=False
        ).values_list("feed_id", flat=True)

        # Get feed items with incomplete clips
        incomplete_feed_items = (
            ClipUserView.objects.filter(user=user, duration__lt=90)
            .values_list("clip__feed_item", flat=True)
            .distinct()
        )

        if avg_feed_embedding is None:
            return Response(
                {"detail": "Not enough data to make recommendations."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Calculate the time decay factor
        current_time = timezone.now()

        base_query = (
            Clip.objects.filter(feed_item__feed__is_english=True)
            .select_related("feed_item__feed")
            .prefetch_related("user_views")
            .annotate(
                feed_score=CosineDistance(
                    "feed_item__feed__topic_embedding", avg_feed_embedding
                ),
                feed_popularity=F("feed_item__feed__popularity_percentile"),
                days_old=Extract(current_time - F("created_at"), "day"),
                recency_score=ExpressionWrapper(
                    1 / (1 + F("days_old") / 7), output_field=FloatField()
                ),
            )
            .exclude(transcript_embedding=[0] * 768)
            .exclude(feed_item__feed__topic_embedding=[0] * 768)
            .exclude(id__in=exclude_clip_ids)
            .exclude(user_views__user=user)
            .exclude(feed_item__feed__in=recent_feeds)
            .exclude(feed_item__feed__id__in=blocked_feeds)
            .exclude(feed_item__id__in=incomplete_feed_items)
        )

        if ClipUserView.objects.filter(user=user).count() < 10:
            print("Using cold start")
            # Cold start: use only feed embeddings if no clip data is available
            ranked_clips = base_query.annotate(
                combined_score=Case(
                    When(
                        feed_score__isnull=False,
                        then=(1 - F("feed_score"))
                        + F("feed_popularity") * 0.25
                        + F("recency_score") * 0.5,
                    ),
                    default=Value(0),
                    output_field=FloatField(),
                ),
            )
        else:
            print("Using warm start")
            # Get average embedding of clips the user has viewed or scored highly
            avg_positive_clip_embedding = Clip.objects.filter(
                user_views__user=user, user_views__duration__gt=90
            ).aggregate(Avg("transcript_embedding"))["transcript_embedding__avg"]

            # Get negative average clip embedding (views < 30)
            avg_negative_clip_embedding = Clip.objects.filter(
                user_views__user=user, user_views__duration__lt=30
            ).aggregate(Avg("transcript_embedding"))["transcript_embedding__avg"]

            # Use both feed and clip embeddings for ranking
            ranked_clips = base_query.annotate(
                positive_clip_score=CosineDistance(
                    "transcript_embedding", avg_positive_clip_embedding
                ),
                negative_clip_score=CosineDistance(
                    "transcript_embedding", avg_negative_clip_embedding
                ),
                combined_score=Case(
                    When(
                        feed_score__isnull=False,
                        positive_clip_score__isnull=False,
                        negative_clip_score__isnull=False,
                        then=(1 - F("feed_score"))
                        + (1 - F("positive_clip_score"))
                        + F("negative_clip_score")
                        + F("feed_popularity") * 0.25
                        + F("recency_score") * 0.5,
                    ),
                    default=Value(0),
                    output_field=FloatField(),
                ),
            )

        # Use window function to get the top clip per feed
        final_clips = (
            ranked_clips.annotate(
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=F("feed_item__feed"),
                    order_by=F("combined_score").desc(),
                )
            )
            .filter(row_number=1)
            .order_by("-combined_score")[:9]
        )

        # Get a random clip
        one_week_ago = timezone.now() - timedelta(days=7)
        random_clip = (
            Clip.objects.filter(
                created_at__gte=one_week_ago,
                feed_item__feed__is_english=True,
            )
            .exclude(user_views__user=user)
            .exclude(id__in=exclude_clip_ids)
            .exclude(
                feed_item__feed__in=Subquery(final_clips.values("feed_item__feed"))
            )
            .order_by("?")
            .first()
        )

        final_clips = list(final_clips)
        if random_clip:
            random_index = random.randint(0, len(final_clips))
            final_clips.insert(random_index, random_clip)

        return final_clips


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Feed.objects.all().filter(is_english=True)
    serializer_class = serializers.FeedSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Feed.objects.all().filter(is_english=True)
        search_query = self.request.query_params.get("search", None)

        if search_query:
            if connection.vendor == "postgresql":
                # Use fuzzy search for PostgreSQL (production mode)
                queryset = queryset.annotate(
                    similarity=TrigramSimilarity("name", search_query),
                )
                queryset = queryset.filter(
                    Q(similarity__gt=0.1)  # Similarity threshold or
                    | Q(name__icontains=search_query)  # Basic search
                ).order_by("-similarity")
            else:
                # Use basic search for SQLite (debug mode)
                queryset = queryset.filter(name__icontains=search_query)

        return queryset


class HistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.HistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ClipUserView.objects.filter(user=self.request.user)
            .select_related("clip__feed_item__feed")
            .order_by("-created_at")[:10]
        )


class ViewViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ClipUserViewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClipUserView.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        clip_id = request.data.get("clip")
        duration = request.data.get("duration", 0)

        clip_user_view, created = ClipUserView.objects.get_or_create(
            user=request.user, clip_id=clip_id, defaults={"duration": duration}
        )

        if not created and duration > clip_user_view.duration:
            print(f"[VIEW] {request.user.username} viewed {clip_id} up to {duration}%")
            clip_user_view.duration = duration
            clip_user_view.save()

        serializer = self.get_serializer(clip_user_view)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )


class FeedUserInterestViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.FeedUserInterestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FeedUserInterest.objects.filter(user=self.request.user).order_by(
            "created_at"
        )

    def create(self, request, *args, **kwargs):
        feed_id = request.data.get("feed_id")
        is_interested = request.data.get("is_interested", True)

        # Try to get an existing instance
        instance = FeedUserInterest.objects.filter(
            user=request.user, feed_id=feed_id
        ).first()

        if instance:
            # Update existing instance
            instance.is_interested = is_interested
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        else:
            # Create new instance
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(APIView):
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        username = request.data.get("username", "").lower()
        email = request.data.get("email", "").lower()
        password = request.data.get("password")

        if not username or not email or not password:
            return Response(
                {"error": "Username, email, and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"error": "Invalid email format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate password strength
        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[A-Z]", password):
            return Response(
                {"error": "Password must contain at least one uppercase letter"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[a-z]", password):
            return Response(
                {"error": "Password must contain at least one lowercase letter"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"\d", password):
            return Response(
                {"error": "Password must contain at least one digit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "user_id": user.pk,
                    "username": user.username,
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )
        except IntegrityError as e:
            if "username" in str(e):
                return Response(
                    {"error": "A user with that username already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif "email" in str(e):
                return Response(
                    {"error": "A user with that email already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {"error": "A user with that username or email already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )


class CustomAuthToken(ObtainAuthToken):
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "").lower()
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Both username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "user_id": user.pk,
                    "username": user.username,
                    "email": user.email,
                }
            )
        else:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Create reset link
        reset_link = request.build_absolute_uri(
            reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        )

        # Send email using Resend
        resend.api_key = settings.RESEND_API_KEY
        r = resend.Emails.send(
            {
                "from": "noreply@trycodec.com",
                "to": email,
                "subject": "Password Reset Request",
                "html": f"Click <a href='{reset_link}'>here</a> to reset your password.",
            }
        )

        return Response(
            {"message": "Password reset email sent"}, status=status.HTTP_200_OK
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasswordResetFormView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            return render(
                request,
                "web/password_reset_form.html",
                {"uidb64": uidb64, "token": token},
            )
        else:
            return render(request, "web/password_reset_invalid.html")

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            new_password = request.POST.get("new_password")
            if new_password:
                user.set_password(new_password)
                user.save()
                return JsonResponse({"message": "Password has been reset successfully"})
            else:
                return JsonResponse({"error": "New password is required"}, status=400)
        else:
            return JsonResponse({"error": "Invalid reset link"}, status=400)
