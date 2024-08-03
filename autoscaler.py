import os
import time
import logging
from typing import Dict

import redis
from django.conf import settings

# Django setup
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "codec.settings")
django.setup()

# Autoscaler configuration
MIN_WORKERS = 1
MAX_WORKERS = 5
QUEUE_THRESHOLD_PER_WORKER = 20
CHECK_INTERVAL = 60  # seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Redis connection details from Django settings
REDIS_URL = settings.CELERY_BROKER_URL
logger.info(f"Connecting to Redis: {REDIS_URL}")

# Connect to Redis
redis_client = redis.from_url(REDIS_URL)


def get_queue_length() -> Dict[str, int]:
    all_keys = redis_client.keys("celery*")
    logger.info(f"All celery-related keys: {all_keys}")

    total_tasks = 0
    queue_lengths = {}

    for key in all_keys:
        key_name = key.decode("utf-8")
        key_type = redis_client.type(key).decode("utf-8")

        if key_type == "list":
            length = redis_client.llen(key)
            queue_lengths[key_name] = length
            total_tasks += length
        elif key_type == "string":
            value = redis_client.get(key)
            logger.info(f"Content of '{key_name}': {value}")
        else:
            logger.info(f"Key '{key_name}' is of type '{key_type}'")

    logger.info(f"Queue lengths: {queue_lengths}")
    logger.info(f"Total tasks: {total_tasks}")

    return {"queue_lengths": queue_lengths, "total": total_tasks}


def get_current_worker_count():
    # This function should be implemented to get the current number of workers
    # For now, we'll return a dummy value
    return 1


def scale_workers(target_count: int):
    # This function should be implemented to scale the number of workers
    # For now, we'll just log the scaling action
    current_count = get_current_worker_count()
    logger.info(f"Scaling workers from {current_count} to {target_count}")


def main():
    while True:
        try:
            queue_stats = get_queue_length()
            total_tasks = queue_stats["total"]
            current_workers = get_current_worker_count()

            target_workers = min(
                max(total_tasks // QUEUE_THRESHOLD_PER_WORKER, MIN_WORKERS), MAX_WORKERS
            )

            logger.info(f"Current queue length: {total_tasks}")
            logger.info(f"Current workers: {current_workers}")
            logger.info(f"Target workers: {target_workers}")

            if target_workers != current_workers:
                scale_workers(target_workers)
            else:
                logger.info(
                    f"No scaling needed. Current workers: {current_workers}, Queue length: {total_tasks}"
                )

        except Exception as e:
            logger.error(f"Error in autoscaler: {str(e)}", exc_info=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
