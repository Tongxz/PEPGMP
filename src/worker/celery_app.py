"""
Celery application configuration for PEPGMP background task processing.
"""

import os
from celery import Celery
from src.config.env_config import config

# Create Celery app
celery_app = Celery('pepgmp')

# Build Redis URL with password
redis_password = config.redis_password
redis_url = f'redis://:{redis_password}@{config.redis_host}:{config.redis_port}/{config.redis_db}'

# Configure broker and backend
# Using Redis as both broker and result backend
celery_app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    # Task settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks from installed modules
celery_app.autodiscover_tasks(['src.worker.tasks'])

if __name__ == '__main__':
    celery_app.start()
