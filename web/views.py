from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Exists, OuterRef, Subquery
from web import serializers
from web.models import (
    Clip,
    ClipUserView,
    ClipUserScore,
    UserFeedFollow,
    UserTopic,
)


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ClipSerializer
    permission_classes = [permissions.IsAuthenticated]

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


class HistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.HistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            ClipUserView.objects.filter(user=self.request.user)
            .select_related("clip__feed_item__feed")
            .order_by("-created_at")
        )


class ViewViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ClipUserViewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ClipUserView.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserTopicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserTopic.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserTopicViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserTopicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserTopic.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserFeedFollowViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserFeedFollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserFeedFollow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
