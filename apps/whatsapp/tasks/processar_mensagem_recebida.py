"""Disponibiliza mensagens recebidas para a orquestracao assincrona."""

import logging
from uuid import UUID

from celery import shared_task

from apps.atendimento.models import Mensagem

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def processar_mensagem_recebida(mensagem_id: str, correlacao: str) -> bool:
    """Confirma idempotentemente uma entrada pronta para processamento posterior."""
    try:
        identificador = UUID(mensagem_id)
    except ValueError:
        logger.warning(
            "mensagem_recebida_invalida",
            extra={"correlacao": correlacao, "mensagem_id": mensagem_id},
        )
        return False
    existe = Mensagem.objects.filter(
        pk=identificador,
        direcao=Mensagem.Direcao.ENTRADA,
        status=Mensagem.Status.RECEBIDA,
    ).exists()
    logger.info(
        "mensagem_recebida_disponivel" if existe else "mensagem_recebida_ausente",
        extra={"correlacao": correlacao, "mensagem_id": mensagem_id},
    )
    return existe
