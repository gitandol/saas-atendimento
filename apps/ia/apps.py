"""Declara a app Django de inteligencia artificial."""

from django.apps import AppConfig


class IAConfig(AppConfig):
    """Registra modelos e recursos do modulo de IA."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ia"
    verbose_name = "Inteligencia artificial"
