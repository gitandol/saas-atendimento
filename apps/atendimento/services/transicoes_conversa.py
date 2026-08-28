"""Compartilha primitivas atomicas das transicoes de conversa."""

from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Conversa
from apps.atendimento.services.conversas import (
    _auditar_conversa,
    conversa_para_dto,
)
from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.obter_empresa import autorizar_membro


class ConflitoTransicaoConversa(Exception):
    """Indica versao desatualizada ou transicao incompatível com o estado atual."""


def carregar_conversa_bloqueada(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario,
    versao: int,
) -> tuple[Conversa, MembroEmpresa]:
    """Autoriza o ator e bloqueia a conversa do tenant na versao esperada."""
    membro = autorizar_membro(empresa=empresa, ator=ator)
    type(empresa).objects.select_for_update().get(pk=empresa.pk)
    conversa = Conversa.objects.select_for_update().get(
        pk=conversa_id,
        empresa=empresa,
    )
    if conversa.versao != versao:
        raise ConflitoTransicaoConversa(
            "A conversa foi atualizada por outra pessoa. Atualize a caixa."
        )
    return conversa, membro


def exigir_responsavel_ou_admin(
    *, conversa: Conversa, membro: MembroEmpresa, ator: Usuario
) -> None:
    """Restringe a acao ao responsavel atual ou a um administrador."""
    if (
        conversa.atendente_id != ator.id
        and membro.papel != MembroEmpresa.Papel.ADMINISTRADOR
    ):
        raise PermissionDenied


def persistir_transicao(
    *,
    empresa: Empresa,
    conversa: Conversa,
    antes: dict[str, object],
    ator: Usuario,
    origem: str,
    correlacao: str,
    justificativa: str,
    campos: tuple[str, ...],
) -> ConversaDTO:
    """Incrementa a versao, salva e registra a transicao na mesma transacao."""
    conversa.versao += 1
    conversa.save(update_fields=(*campos, "versao", "atualizado_em"))
    _auditar_conversa(
        empresa=empresa,
        conversa=conversa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
        justificativa=justificativa,
    )
    return conversa_para_dto(conversa)


atomic = transaction.atomic
