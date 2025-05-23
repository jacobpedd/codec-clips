import os

from celery import Celery

# set the default Django settings module for the 'celery' program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "codec.settings")

app = Celery("codec")

# all celery-related configuration keys should have a `CELERY_` prefix
app.config_from_object("django.conf:settings", namespace="CELERY")
# load task modules from all registered Django apps
app.autodiscover_tasks()

# Priority settings
app.conf.task_queue_max_priority = 10
app.conf.task_default_priority = 5
