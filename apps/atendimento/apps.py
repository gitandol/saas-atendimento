"""Declara a app Django do dominio de atendimento."""

from django.apps import AppConfig


class AtendimentoConfig(AppConfig):
    """Registra modelos e recursos do atendimento."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.atendimento"
    verbose_name = "Atendimento"
