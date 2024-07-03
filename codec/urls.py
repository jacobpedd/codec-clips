from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from web import views

router = routers.DefaultRouter()
router.register(r"feed", views.FeedViewSet, basename="feed")
router.register(r"view", views.ViewViewSet, basename="view")
router.register(r"history", views.HistoryViewSet, basename="history")
router.register(r"topics", views.UserTopicViewSet, basename="topics")
router.register(r"following", views.UserFeedFollowViewSet, basename="following")

urlpatterns = [
    # put api routes at the root
    path("", include(router.urls)),
    # handles auth for api browser UI
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # django admin interface
    path("admin/", admin.site.urls),
]
