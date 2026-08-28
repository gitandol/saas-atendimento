"""Coordena o envio Celery com retentativas exponenciais limitadas."""

import logging
from uuid import UUID

from celery import shared_task

from apps.whatsapp.services.enviar_mensagem import (
    FALHAS_TRANSITORIAS,
    executar_envio,
    registrar_falha_final,
    registrar_tentativa_transitoria,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=FALHAS_TRANSITORIAS,
    retry_backoff=2,
    retry_jitter=True,
    max_retries=4,
    ignore_result=True,
)
def enviar_mensagem_whatsapp(self, mensagem_id: str, correlacao: str) -> bool:
    """Converte o UUID e repete somente falhas externas transitorias."""
    try:
        identificador = UUID(mensagem_id)
    except ValueError:
        logger.warning(
            "envio_whatsapp_payload_invalido",
            extra={"mensagem_id": mensagem_id, "correlacao": correlacao},
        )
        return False
    try:
        return executar_envio(
            mensagem_id=identificador,
            correlacao=correlacao,
        )
    except FALHAS_TRANSITORIAS as erro:
        tentativa = self.request.retries + 1
        logger.warning(
            "envio_whatsapp_tentativa_transitoria",
            extra={
                "mensagem_id": mensagem_id,
                "correlacao": correlacao,
                "tentativa": tentativa,
                "maximo_tentativas": self.max_retries + 1,
                "erro": type(erro).__name__,
                "metrica": "whatsapp_tentativas_envio_total",
            },
        )
        if self.request.retries >= self.max_retries:
            registrar_falha_final(
                mensagem_id=identificador,
                erro=erro,
                correlacao=correlacao,
            )
        else:
            registrar_tentativa_transitoria(
                mensagem_id=identificador,
                correlacao=correlacao,
            )
        raise
