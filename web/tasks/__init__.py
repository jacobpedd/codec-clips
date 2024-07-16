from celery import signals
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

from web.tasks.crawler_tasks import *
from web.tasks.clipper_tasks import *
from web.tasks.ranker_tasks import *


@signals.beat_init.connect
@signals.celeryd_init.connect
def init_sentry(**kwargs):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[CeleryIntegration(monitor_beat_tasks=True)],
        environment="production" if not settings.DEBUG else "development",
    )
