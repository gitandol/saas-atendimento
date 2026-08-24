"""Configuracao do app de empresas."""

from django.apps import AppConfig


class EmpresasConfig(AppConfig):
    """Registra o app responsavel pelas empresas do tenant."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.empresas"
    label = "empresas"
