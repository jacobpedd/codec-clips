from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from web.models import ClipUserView
from web.lib.logsnag import logsnag_insight


@shared_task
def update_active_users():
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Calculate daily active users
    daily_active_users = (
        ClipUserView.objects.filter(created_at__gte=yesterday)
        .values("user")
        .distinct()
        .count()
    )

    # Calculate weekly active users
    weekly_active_users = (
        ClipUserView.objects.filter(created_at__gte=week_ago)
        .values("user")
        .distinct()
        .count()
    )

    # Calculate monthly active users
    monthly_active_users = (
        ClipUserView.objects.filter(created_at__gte=month_ago)
        .values("user")
        .distinct()
        .count()
    )

    # Send insights to LogSnag
    try:
        logsnag_insight("Daily Active Users", daily_active_users, "☀️")
        logsnag_insight("Weekly Active Users", weekly_active_users, "📅")
        logsnag_insight("Monthly Active Users", monthly_active_users, "🗓️")
    except Exception as e:
        print(f"Error sending active users insight to LogSnag: {e}")

    return {
        "daily_active_users": daily_active_users,
        "weekly_active_users": weekly_active_users,
        "monthly_active_users": monthly_active_users,
    }
