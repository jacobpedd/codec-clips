import json
import requests

from django.conf import settings


def logsnag_log(event, description, icon, channel, user_id=None, notify=False):
    if settings.DEBUG:
        return

    url = "https://api.logsnag.com/v1/log"
    payload = {
        "project": "codec",
        "channel": channel,
        "event": event,
        "description": description,
        "icon": icon,
        "notify": notify,
    }

    if user_id is not None:
        payload["user_id"] = f"{user_id}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LOGSNAG_API_KEY}",
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending event to LogSnag: {e}")


def logsnag_insight(title, value, icon):
    if settings.DEBUG:
        return

    url = "https://api.logsnag.com/v1/insight"
    payload = {
        "project": "codec",
        "title": title,
        "value": str(value),  # Ensure value is a string
        "icon": icon,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LOGSNAG_API_KEY}",
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending insight to LogSnag: {e}")
