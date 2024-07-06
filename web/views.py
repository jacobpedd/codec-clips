import re
from rest_framework import viewsets, filters, status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Exists, OuterRef, Subquery
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, connection
from django.db.models import Q
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.conf import settings
from django.urls import reverse
from web import serializers
from web.models import (
    Clip,
    ClipUserView,
    ClipUserScore,
    UserFeedFollow,
    UserTopic,
    Feed,
)
import resend


class QueueViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ClipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Clip.objects.annotate(
                score=Subquery(
                    ClipUserScore.objects.filter(clip=OuterRef("pk"), user=user).values(
                        "score"
                    )[:1]
                )
            )
            .filter(
                ~Exists(ClipUserView.objects.filter(user=user, clip=OuterRef("pk")))
            )
            .select_related("feed_item__feed")
            .order_by("-score")
        )


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Feed.objects.all()
    serializer_class = serializers.FeedSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Feed.objects.all()
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
            .order_by("-created_at")
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
            clip_user_view.duration = duration
            clip_user_view.save()

        serializer = self.get_serializer(clip_user_view)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )


class UserTopicViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserTopicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserTopic.objects.filter(user=self.request.user).order_by("created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserFeedFollowViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserFeedFollowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserFeedFollow.objects.filter(user=self.request.user).order_by(
            "created_at"
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
                "from": "noreply@readbox.app",  # TODO: Change to prod domain
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
