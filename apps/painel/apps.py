"""Configura o modulo de painel operacional."""

from django.apps import AppConfig


class PainelConfig(AppConfig):
    """Registra o dashboard operacional na aplicacao."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.painel"
