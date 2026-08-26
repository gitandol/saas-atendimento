"""Declara a app Django de conexao com WhatsApp."""

from django.apps import AppConfig


class WhatsAppConfig(AppConfig):
    """Registra modelos e recursos do modulo WhatsApp."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.whatsapp"
    verbose_name = "WhatsApp"
