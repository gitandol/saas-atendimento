"""Abre, reabre e finaliza conversas com auditoria."""

from typing import Any
from uuid import UUID

from django.db import transaction

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Contato, Conversa
from apps.atendimento.services.contatos import contato_para_dto
from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa
from apps.empresas.services.obter_empresa import autorizar_membro


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
        versao=conversa.versao,
        finalizada_em=conversa.finalizada_em,
        criado_em=conversa.criado_em,
        atualizado_em=conversa.atualizado_em,
        ultima_mensagem_texto=(
            conversa.ultima_mensagem.texto if conversa.ultima_mensagem_id else ""
        ),
        atendente_nome=(
            conversa.atendente.get_full_name() or conversa.atendente.email
            if conversa.atendente_id
            else ""
        ),
    )


@transaction.atomic
def marcar_como_lida(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    ator: Usuario,
    correlacao: str,
) -> ConversaDTO:
    """Zera nao lidas de uma conversa autorizada e registra a alteracao."""
    autorizar_membro(empresa=empresa, ator=ator)
    conversa = (
        Conversa.objects.select_for_update()
        .select_related("contato", "atendente", "ultima_mensagem")
        .get(pk=conversa_id, empresa=empresa)
    )
    if conversa.contagem_nao_lida == 0:
        return conversa_para_dto(conversa)
    antes = snapshot_conversa(conversa)
    conversa.contagem_nao_lida = 0
    conversa.save(update_fields=("contagem_nao_lida", "atualizado_em"))
    _auditar_conversa(
        empresa=empresa,
        conversa=conversa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        ator=ator,
        origem="api_caixa_entrada",
        correlacao=correlacao,
    )
    return conversa_para_dto(conversa)


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
        "versao": conversa.versao,
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
    justificativa: str = "",
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
        justificativa=justificativa,
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
        conversa.modo = Conversa.Modo.IA
        conversa.atendente = None
        conversa.finalizada_em = None
        conversa.versao += 1
        conversa.save(
            update_fields=(
                "estado",
                "modo",
                "atendente",
                "finalizada_em",
                "versao",
                "atualizado_em",
            )
        )
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
