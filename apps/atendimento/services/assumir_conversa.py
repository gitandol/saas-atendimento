"""Transfere uma conversa da IA para um atendente."""

from uuid import UUID

from django.db import transaction

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Conversa
from apps.atendimento.services.conversas import snapshot_conversa
from apps.atendimento.services.transicoes_conversa import (
    ConflitoTransicaoConversa,
    carregar_conversa_bloqueada,
    persistir_transicao,
)
from apps.contas.models import Usuario
from apps.empresas.models import Empresa

__all__ = ["ConflitoTransicaoConversa", "assumir_conversa"]


@transaction.atomic
def assumir_conversa(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario,
    versao: int,
    justificativa: str,
    origem: str,
    correlacao: str,
) -> ConversaDTO:
    """Atribui atomicamente uma conversa IA/ABERTA ao atendente autorizado."""
    conversa, _membro = carregar_conversa_bloqueada(
        empresa=empresa,
        conversa_id=conversa_id,
        ator=ator,
        versao=versao,
    )
    if conversa.estado != Conversa.Estado.ABERTA or conversa.modo != Conversa.Modo.IA:
        raise ConflitoTransicaoConversa(
            "Somente conversas abertas da IA podem ser assumidas."
        )
    antes = snapshot_conversa(conversa)
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = ator
    return persistir_transicao(
        empresa=empresa,
        conversa=conversa,
        antes=antes,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
        justificativa=justificativa,
        campos=("modo", "atendente"),
    )
