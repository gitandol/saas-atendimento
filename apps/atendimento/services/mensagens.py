"""Registra mensagens e atualiza seus agregados de forma atomica."""

from typing import Any
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.atendimento.dto import MensagemDTO
from apps.atendimento.models import Contato, Conversa, Mensagem
from apps.atendimento.services.contatos import snapshot_contato
from apps.atendimento.services.conversas import snapshot_conversa
from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


def mensagem_para_dto(mensagem: Mensagem) -> MensagemDTO:
    """Converte uma mensagem persistida no contrato imutavel."""
    return MensagemDTO(
        id=mensagem.id,
        conversa_id=mensagem.conversa_id,
        direcao=mensagem.direcao,
        autor=mensagem.autor,
        texto=mensagem.texto,
        identificador_externo=mensagem.identificador_externo,
        status=mensagem.status,
        erro_sanitizado=mensagem.erro_sanitizado,
        enviado_em=mensagem.enviado_em,
        entregue_em=mensagem.entregue_em,
        processamento_enfileirado=mensagem.processamento_enfileirado,
        processamento_enfileirado_em=mensagem.processamento_enfileirado_em,
        criado_em=mensagem.criado_em,
    )


def snapshot_mensagem(mensagem: Mensagem) -> dict[str, Any]:
    """Produz metadados auditaveis sem copiar o texto da conversa."""
    return {
        "conversa_id": str(mensagem.conversa_id),
        "direcao": mensagem.direcao,
        "autor": mensagem.autor,
        "texto_tamanho": len(mensagem.texto),
        "identificador_externo": mensagem.identificador_externo,
        "status": mensagem.status,
        "erro_sanitizado": mensagem.erro_sanitizado,
        "enviado_em": mensagem.enviado_em.isoformat() if mensagem.enviado_em else None,
        "entregue_em": (
            mensagem.entregue_em.isoformat() if mensagem.entregue_em else None
        ),
        "processamento_enfileirado_em": (
            mensagem.processamento_enfileirado_em.isoformat()
            if mensagem.processamento_enfileirado_em
            else None
        ),
        "processamento_enfileirado": mensagem.processamento_enfileirado,
    }


def _auditar_criacao(
    *,
    empresa: Empresa,
    objeto,
    depois: dict[str, Any],
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> None:
    """Registra a criacao de um objeto do agregado de atendimento."""
    registrar_alteracao(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        depois=depois,
        campos_alterados=list(depois),
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )


def _auditar_atualizacao(
    *,
    empresa: Empresa,
    objeto,
    antes: dict[str, Any],
    depois: dict[str, Any],
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> None:
    """Registra os campos alterados de um agregado existente."""
    registrar_alteracao(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
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
def registrar_mensagem(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    direcao: str,
    autor: str,
    texto: str,
    identificador_externo: str,
    status: str,
    erro_sanitizado: str = "",
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> MensagemDTO:
    """Persiste uma mensagem idempotente e atualiza conversa e contato."""
    type(empresa).objects.select_for_update().get(pk=empresa.pk)
    if identificador_externo:
        existente = Mensagem.objects.filter(
            empresa=empresa,
            identificador_externo=identificador_externo,
        ).first()
        if existente is not None:
            return mensagem_para_dto(existente)

    conversa = (
        Conversa.objects.select_for_update()
        .select_related("contato")
        .get(pk=conversa_id, empresa=empresa)
    )
    if conversa.estado != Conversa.Estado.ABERTA:
        raise ValidationError({"conversa": "A conversa esta finalizada."})
    if (
        direcao == Mensagem.Direcao.SAIDA
        and autor == Mensagem.Autor.IA
        and conversa.modo != Conversa.Modo.IA
    ):
        raise ValidationError({"conversa": "A conversa esta em atendimento humano."})
    if (
        direcao == Mensagem.Direcao.SAIDA
        and autor == Mensagem.Autor.ATENDENTE
        and (
            conversa.modo != Conversa.Modo.HUMANO
            or ator is None
            or conversa.atendente_id != ator.id
        )
    ):
        raise PermissionDenied
    contato = Contato.objects.select_for_update().get(
        pk=conversa.contato_id,
        empresa=empresa,
        excluido_em__isnull=True,
    )
    mensagem = Mensagem(
        empresa=empresa,
        conversa=conversa,
        direcao=direcao,
        autor=autor,
        texto=texto,
        identificador_externo=identificador_externo,
        status=status,
        erro_sanitizado=erro_sanitizado,
    )
    mensagem.full_clean()
    mensagem.save()

    antes_conversa = snapshot_conversa(conversa)
    conversa.ultima_mensagem = mensagem
    if direcao == Mensagem.Direcao.ENTRADA:
        conversa.contagem_nao_lida += 1
        conversa.contagem_nao_respondida += 1
    elif autor in {Mensagem.Autor.IA, Mensagem.Autor.ATENDENTE}:
        conversa.contagem_nao_respondida = 0
    conversa.save(
        update_fields=(
            "ultima_mensagem",
            "contagem_nao_lida",
            "contagem_nao_respondida",
            "atualizado_em",
        )
    )

    antes_contato = snapshot_contato(contato)
    if contato.primeiro_contato_em is None:
        contato.primeiro_contato_em = mensagem.criado_em
    contato.ultimo_contato_em = mensagem.criado_em
    contato.save(
        update_fields=("primeiro_contato_em", "ultimo_contato_em", "atualizado_em")
    )

    _auditar_criacao(
        empresa=empresa,
        objeto=mensagem,
        depois=snapshot_mensagem(mensagem),
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
    _auditar_atualizacao(
        empresa=empresa,
        objeto=conversa,
        antes=antes_conversa,
        depois=snapshot_conversa(conversa),
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
    _auditar_atualizacao(
        empresa=empresa,
        objeto=contato,
        antes=antes_contato,
        depois=snapshot_contato(contato),
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
    return mensagem_para_dto(mensagem)
