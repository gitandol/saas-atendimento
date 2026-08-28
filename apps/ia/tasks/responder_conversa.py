"""Coordena a geracao assincrona de uma resposta automatica."""

import logging
from uuid import UUID

from celery import shared_task

from apps.ia.services.gerar_resposta_atendimento import (
    RespostaAutomaticaNaoPermitida,
    gerar_resposta_atendimento,
)

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def responder_conversa(
    conversa_id: str, mensagem_entrada_id: str, correlacao: str
) -> bool:
    """Converte UUIDs da fila e delega toda a regra ao service de dominio."""
    try:
        conversa_uuid = UUID(conversa_id)
        mensagem_uuid = UUID(mensagem_entrada_id)
    except ValueError:
        logger.warning(
            "resposta_ia_payload_invalido",
            extra={
                "conversa_id": conversa_id,
                "mensagem_entrada_id": mensagem_entrada_id,
                "correlacao": correlacao,
            },
        )
        return False
    try:
        gerar_resposta_atendimento(
            conversa_id=conversa_uuid,
            mensagem_entrada_id=mensagem_uuid,
            correlacao=correlacao,
        )
    except RespostaAutomaticaNaoPermitida:
        logger.info(
            "resposta_ia_ignorada",
            extra={
                "conversa_id": conversa_id,
                "mensagem_entrada_id": mensagem_entrada_id,
                "correlacao": correlacao,
            },
        )
        return False
    return True
