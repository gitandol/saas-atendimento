"""Abre, reabre e finaliza conversas com auditoria."""

from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Contato, Conversa
from apps.atendimento.services.contatos import contato_para_dto
from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


def conversa_para_dto(conversa: Conversa) -> ConversaDTO:
    """Converte uma conversa e seu contato no contrato imutavel."""
    return ConversaDTO(
        id=conversa.id,
        contato=contato_para_dto(conversa.contato),
        modo=conversa.modo,
        estado=conversa.estado,
        atendente_id=conversa.atendente_id,
        ultima_mensagem_id=conversa.ultima_mensagem_id,
        contagem_nao_lida=conversa.contagem_nao_lida,
        finalizada_em=conversa.finalizada_em,
        criado_em=conversa.criado_em,
        atualizado_em=conversa.atualizado_em,
    )


def snapshot_conversa(conversa: Conversa) -> dict[str, Any]:
    """Produz snapshot auditavel do estado operacional da conversa."""
    return {
        "contato_id": str(conversa.contato_id),
        "modo": conversa.modo,
        "estado": conversa.estado,
        "atendente_id": str(conversa.atendente_id) if conversa.atendente_id else None,
        "ultima_mensagem_id": (
            str(conversa.ultima_mensagem_id) if conversa.ultima_mensagem_id else None
        ),
        "contagem_nao_lida": conversa.contagem_nao_lida,
        "finalizada_em": (
            conversa.finalizada_em.isoformat() if conversa.finalizada_em else None
        ),
    }


def _auditar_conversa(
    *,
    empresa: Empresa,
    conversa: Conversa,
    acao: str,
    antes: dict[str, Any],
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> None:
    """Registra o diff funcional de uma conversa."""
    depois = snapshot_conversa(conversa)
    registrar_alteracao(
        empresa=empresa,
        objeto=conversa,
        acao=acao,
        antes=antes,
        depois=depois,
        campos_alterados=[
            campo for campo, valor in depois.items() if antes.get(campo) != valor
        ],
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )


@transaction.atomic
def obter_ou_abrir_conversa(
    *,
    empresa: Empresa,
    contato_id: UUID,
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> ConversaDTO:
    """Retorna a conversa aberta ou reabre explicitamente a mais recente."""
    type(empresa).objects.select_for_update().get(pk=empresa.pk)
    contato = Contato.objects.select_for_update().get(
        pk=contato_id,
        empresa=empresa,
        excluido_em__isnull=True,
    )
    conversa = (
        Conversa.objects.select_for_update()
        .select_related("contato")
        .filter(empresa=empresa, contato=contato)
        .order_by("estado", "-atualizado_em", "-id")
        .first()
    )
    if conversa is None:
        conversa = Conversa(empresa=empresa, contato=contato)
        conversa.full_clean()
        conversa.save()
        _auditar_conversa(
            empresa=empresa,
            conversa=conversa,
            acao=EventoAuditoria.Acao.CRIACAO,
            antes={},
            ator=ator,
            origem=origem,
            correlacao=correlacao,
        )
    elif conversa.estado == Conversa.Estado.FINALIZADA:
        antes = snapshot_conversa(conversa)
        conversa.estado = Conversa.Estado.ABERTA
        conversa.finalizada_em = None
        conversa.save(update_fields=("estado", "finalizada_em", "atualizado_em"))
        _auditar_conversa(
            empresa=empresa,
            conversa=conversa,
            acao=EventoAuditoria.Acao.ATUALIZACAO,
            antes=antes,
            ator=ator,
            origem=origem,
            correlacao=correlacao,
        )
    return conversa_para_dto(conversa)


@transaction.atomic
def finalizar_conversa(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> ConversaDTO:
    """Finaliza a conversa sem remover qualquer mensagem do historico."""
    type(empresa).objects.select_for_update().get(pk=empresa.pk)
    conversa = (
        Conversa.objects.select_for_update()
        .select_related("contato")
        .get(pk=conversa_id, empresa=empresa)
    )
    if conversa.estado == Conversa.Estado.FINALIZADA:
        return conversa_para_dto(conversa)
    antes = snapshot_conversa(conversa)
    conversa.estado = Conversa.Estado.FINALIZADA
    conversa.finalizada_em = timezone.now()
    conversa.save(update_fields=("estado", "finalizada_em", "atualizado_em"))
    _auditar_conversa(
        empresa=empresa,
        conversa=conversa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
    return conversa_para_dto(conversa)
