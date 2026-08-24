"""Configura o aplicativo de auditoria."""

from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    """Registra a infraestrutura de auditoria no Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditoria"
