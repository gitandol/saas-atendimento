"""Finaliza explicitamente uma conversa aberta."""

from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Conversa
from apps.atendimento.services.conversas import snapshot_conversa
from apps.atendimento.services.transicoes_conversa import (
    ConflitoTransicaoConversa,
    carregar_conversa_bloqueada,
    exigir_responsavel_ou_admin,
    persistir_transicao,
)
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


@transaction.atomic
def finalizar_conversa(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario,
    versao: int,
    justificativa: str,
    origem: str,
    correlacao: str,
) -> ConversaDTO:
    """Finaliza sob lock e impede novas saidas manuais ou automaticas."""
    conversa, membro = carregar_conversa_bloqueada(
        empresa=empresa,
        conversa_id=conversa_id,
        ator=ator,
        versao=versao,
    )
    if conversa.estado != Conversa.Estado.ABERTA:
        raise ConflitoTransicaoConversa("A conversa ja esta finalizada.")
    if conversa.modo == Conversa.Modo.HUMANO:
        exigir_responsavel_ou_admin(conversa=conversa, membro=membro, ator=ator)
    antes = snapshot_conversa(conversa)
    conversa.estado = Conversa.Estado.FINALIZADA
    conversa.finalizada_em = timezone.now()
    return persistir_transicao(
        empresa=empresa,
        conversa=conversa,
        antes=antes,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
        justificativa=justificativa,
        campos=("estado", "finalizada_em"),
    )
