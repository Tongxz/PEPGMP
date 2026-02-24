"""
Celery task definitions for PEPGMP.
"""

from .celery_app import celery_app


@celery_app.task(name='src.worker.tasks.health_check')
def health_check():
    """
    Health check task to verify Celery worker is functioning.
    """
    return {'status': 'ok', 'message': 'Celery worker is healthy'}
