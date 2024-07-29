from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from web import views

router = routers.DefaultRouter()
router.register(r"queue", views.QueueViewSet, basename="queue")
router.register(r"feed_recs", views.RecommendedFeedsViewSet, basename="feed_recs")
router.register(r"feed", views.FeedViewSet, basename="feed")
router.register(r"view", views.ViewViewSet, basename="view")
router.register(r"history", views.HistoryViewSet, basename="history")
router.register(r"following", views.FeedUserInterestViewSet, basename="following")

urlpatterns = [
    # put api routes at the root
    path("", include(router.urls)),
    # handles auth for api browser UI
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # django admin interface
    path("admin/", admin.site.urls),
    # get a auth token for mobile
    path("auth/", views.CustomAuthToken.as_view(), name="auth_token"),
    # register a new user
    path("register/", views.RegisterView.as_view(), name="register"),
    # views for password reset
    path(
        "password_reset/",
        views.PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "reset-password/<str:uidb64>/<str:token>/",
        views.PasswordResetFormView.as_view(),
        name="password_reset_confirm",
    ),
]
