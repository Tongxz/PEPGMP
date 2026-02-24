#!/bin/bash
# 启动Celery worker

cd /Users/zhou/Code/PEPGMP

echo "启动Celery worker..."
echo "Redis URL: redis://:pepgmp_dev_redis@localhost:6379/0"

# 启动worker
celery -A src.worker.celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --hostname=worker@%h \
    --queues=default \
    --max-tasks-per-child=1000