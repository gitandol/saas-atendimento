"""Configuracao do app de contas."""

from django.apps import AppConfig


class ContasConfig(AppConfig):
    """Registra o app responsavel pelos usuarios da plataforma."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contas"
    label = "contas"
