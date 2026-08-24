"""Configura o worker Celery a partir dos settings Django."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.producao")

app = Celery("atendimento")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
