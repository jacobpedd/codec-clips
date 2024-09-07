from django.urls import path
from . import views

urlpatterns = [
    path("", views.topic_hierarchy, name="topic_hierarchy"),
    path("update-topic-parent/", views.update_topic_parent, name="update_topic_parent"),
]
