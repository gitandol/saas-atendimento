"""Expoe tasks Celery do modulo WhatsApp."""

from apps.whatsapp.tasks.processar_mensagem_recebida import (
    processar_mensagem_recebida,
)

__all__ = ["processar_mensagem_recebida"]
