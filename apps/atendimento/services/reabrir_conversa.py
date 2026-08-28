"""Reabre explicitamente uma conversa finalizada."""

from uuid import UUID

from django.core.exceptions import ValidationError
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


@transaction.atomic
def reabrir_conversa(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario,
    versao: int,
    modo: str = Conversa.Modo.IA,
    justificativa: str,
    origem: str,
    correlacao: str,
) -> ConversaDTO:
    """Reabre para IA ou atribui o proprio ator quando o modo for humano."""
    if modo not in Conversa.Modo.values:
        raise ValidationError({"modo": "Informe IA ou HUMANO."})
    conversa, _membro = carregar_conversa_bloqueada(
        empresa=empresa,
        conversa_id=conversa_id,
        ator=ator,
        versao=versao,
    )
    if conversa.estado != Conversa.Estado.FINALIZADA:
        raise ConflitoTransicaoConversa("Somente conversas finalizadas podem reabrir.")
    antes = snapshot_conversa(conversa)
    conversa.estado = Conversa.Estado.ABERTA
    conversa.modo = modo
    conversa.atendente = ator if modo == Conversa.Modo.HUMANO else None
    conversa.finalizada_em = None
    return persistir_transicao(
        empresa=empresa,
        conversa=conversa,
        antes=antes,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
        justificativa=justificativa,
        campos=("estado", "modo", "atendente", "finalizada_em"),
    )
