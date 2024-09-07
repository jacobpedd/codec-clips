from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from web.models import Topic  # Import the Topic model from the web app
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q


# Helper function to check if user is staff
def is_staff(user):
    return user.is_staff


def build_topic_tree(topics):
    topic_dict = {topic.id: {"topic": topic, "children": []} for topic in topics}
    root_topics = []
    for topic in topics:
        if topic.parent_id:
            if topic.parent_id in topic_dict:
                topic_dict[topic.parent_id]["children"].append(topic_dict[topic.id])
        else:
            root_topics.append(topic_dict[topic.id])

    # Sort children recursively
    def sort_children(node):
        node["children"].sort(key=lambda x: x["topic"].name.lower())
        for child in node["children"]:
            sort_children(child)

    for root in root_topics:
        sort_children(root)

    # Sort root topics
    root_topics.sort(key=lambda x: x["topic"].name.lower())

    return root_topics


@login_required
@user_passes_test(is_staff)
def topic_hierarchy(request):
    all_topics = Topic.objects.all().order_by("name")

    orphan_topics = all_topics.filter(
        parent__isnull=True, children__isnull=True
    ).order_by("name")
    connected_topics = all_topics.exclude(id__in=orphan_topics)

    topic_tree = build_topic_tree(connected_topics)

    return render(
        request,
        "topic_manager/topic_hierarchy.html",
        {"orphan_topics": orphan_topics, "topic_tree": topic_tree},
    )


@login_required
@user_passes_test(is_staff)
@require_POST
def update_topic_parent(request):
    try:
        topic_id = request.POST.get("topic_id")
        parent_id = request.POST.get("parent_id")

        topic = get_object_or_404(Topic, id=topic_id)
        if parent_id:
            parent = get_object_or_404(Topic, id=parent_id)
            if topic.is_descendant_of(parent):
                return JsonResponse(
                    {"success": False, "error": "Cannot create circular reference"},
                    status=400,
                )
            topic.parent = parent
        else:
            topic.parent = None
        topic.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
