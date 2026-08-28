"""Devolve uma conversa humana para a IA."""

from uuid import UUID

from django.db import transaction

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
def devolver_para_ia(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario,
    versao: int,
    justificativa: str,
    origem: str,
    correlacao: str,
) -> ConversaDTO:
    """Remove o responsavel atual sem gerar qualquer resposta retroativa."""
    conversa, membro = carregar_conversa_bloqueada(
        empresa=empresa,
        conversa_id=conversa_id,
        ator=ator,
        versao=versao,
    )
    if (
        conversa.estado != Conversa.Estado.ABERTA
        or conversa.modo != Conversa.Modo.HUMANO
    ):
        raise ConflitoTransicaoConversa(
            "Somente conversas humanas abertas podem voltar para a IA."
        )
    exigir_responsavel_ou_admin(conversa=conversa, membro=membro, ator=ator)
    antes = snapshot_conversa(conversa)
    conversa.modo = Conversa.Modo.IA
    conversa.atendente = None
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
