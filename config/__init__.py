"""Configura a aplicacao Django e o worker Celery."""

from config.celery import app as celery_app

__all__ = ("celery_app",)
