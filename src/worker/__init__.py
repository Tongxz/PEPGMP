"""
Celery worker package for PEPGMP background task processing.
"""

from .celery_app import celery_app

__all__ = ['celery_app']
