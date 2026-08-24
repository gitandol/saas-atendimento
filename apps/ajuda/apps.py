"""Configura o aplicativo de ajuda."""

from django.apps import AppConfig


class AjudaConfig(AppConfig):
    """Registra a ajuda contextual no Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ajuda"
