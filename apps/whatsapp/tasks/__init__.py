"""Expoe tasks Celery do modulo WhatsApp."""

from apps.whatsapp.tasks import enviar_mensagem
from apps.whatsapp.tasks.processar_mensagem_recebida import (
    processar_mensagem_recebida,
)

__all__ = ["enviar_mensagem", "processar_mensagem_recebida"]
