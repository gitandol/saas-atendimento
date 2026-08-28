"""Persiste e agenda webhooks Evolution de forma idempotente."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.atendimento.models import Mensagem
from apps.atendimento.services.contatos import obter_ou_criar_contato
from apps.atendimento.services.conversas import obter_ou_abrir_conversa
from apps.atendimento.services.mensagens import registrar_mensagem
from apps.empresas.models import Empresa
from apps.ia.tasks.responder_conversa import responder_conversa
from apps.whatsapp.services.atualizar_status_entrega import atualizar_status_entrega
from apps.whatsapp.services.normalizar_evento import (
    normalizar_evento,
    normalizar_evento_entrega,
)
from apps.whatsapp.services.validar_webhook import validar_webhook

logger = logging.getLogger(__name__)
DURACAO_LEASE_PUBLICACAO = timedelta(minutes=2)


class EnfileiramentoIndisponivel(Exception):
    """Indica que a mensagem persistiu, mas o broker recusou a publicacao."""


@dataclass(frozen=True, slots=True)
class ResultadoRecebimento:
    """Resume o efeito persistente e assincrono do webhook."""

    criado: bool
    mensagem_id: UUID | None
    enfileirado: bool


def _registrar_evento(
    *,
    empresa: Empresa,
    payload: dict[str, Any],
    correlacao: str,
) -> tuple[Mensagem | None, bool]:
    """Cria o agregado uma vez sob bloqueio do tenant."""
    recibo = normalizar_evento_entrega(payload)
    if recibo is not None:
        atualizar_status_entrega(
            empresa=empresa,
            identificador_externo=recibo.identificador_externo,
            status=recibo.status,
            ocorrido_em=recibo.ocorrido_em,
            correlacao=correlacao,
        )
        mensagem = Mensagem.objects.filter(
            empresa=empresa,
            identificador_externo=recibo.identificador_externo,
            direcao=Mensagem.Direcao.SAIDA,
        ).first()
        return mensagem, False
    evento = normalizar_evento(payload)
    if evento is None:
        logger.info(
            "evento_evolution_nao_suportado",
            extra={
                "correlacao": correlacao,
                "empresa_id": str(empresa.pk),
                "tipo_evento": payload.get("event", ""),
            },
        )
        return None, False

    with transaction.atomic():
        Empresa.objects.select_for_update().get(pk=empresa.pk)
        existente = Mensagem.objects.filter(
            empresa=empresa,
            identificador_externo=evento.identificador_externo,
        ).first()
        if existente is not None:
            return existente, False
        contato = obter_ou_criar_contato(
            empresa=empresa,
            numero_telefone=evento.numero_remetente,
            nome=evento.nome_remetente,
            ator=None,
            origem="webhook_evolution",
            correlacao=correlacao,
        )
        conversa = obter_ou_abrir_conversa(
            empresa=empresa,
            contato_id=contato.id,
            ator=None,
            origem="webhook_evolution",
            correlacao=correlacao,
        )
        direcao = (
            Mensagem.Direcao.SAIDA
            if evento.enviado_pela_instancia
            else Mensagem.Direcao.ENTRADA
        )
        autor = (
            Mensagem.Autor.SISTEMA
            if evento.enviado_pela_instancia
            else Mensagem.Autor.CLIENTE
        )
        status = (
            Mensagem.Status.ENVIADA
            if evento.enviado_pela_instancia
            else Mensagem.Status.RECEBIDA
        )
        registrada = registrar_mensagem(
            empresa=empresa,
            conversa_id=conversa.id,
            direcao=direcao,
            autor=autor,
            texto=evento.texto,
            identificador_externo=evento.identificador_externo,
            status=status,
            ator=None,
            origem="webhook_evolution",
            correlacao=correlacao,
        )
        return Mensagem.objects.get(pk=registrada.id), True


def _enfileirar(mensagem: Mensagem, correlacao: str) -> bool:
    """Reivindica, publica e confirma uma entrada com lease recuperavel."""
    if mensagem.direcao != Mensagem.Direcao.ENTRADA:
        return False
    reivindicado_em = timezone.now()
    reivindicado = (
        Mensagem.objects.filter(
            pk=mensagem.pk,
            processamento_enfileirado=False,
        )
        .filter(
            Q(processamento_enfileirado_em__isnull=True)
            | Q(
                processamento_enfileirado_em__lt=(
                    reivindicado_em - DURACAO_LEASE_PUBLICACAO
                )
            )
        )
        .update(processamento_enfileirado_em=reivindicado_em)
    )
    if not reivindicado:
        confirmado = Mensagem.objects.values_list(
            "processamento_enfileirado",
            flat=True,
        ).get(pk=mensagem.pk)
        if confirmado:
            return False
        raise EnfileiramentoIndisponivel
    try:
        responder_conversa.delay(
            str(mensagem.conversa_id),
            str(mensagem.pk),
            correlacao,
        )
    except Exception as erro:
        Mensagem.objects.filter(
            pk=mensagem.pk,
            processamento_enfileirado=False,
            processamento_enfileirado_em=reivindicado_em,
        ).update(processamento_enfileirado_em=None)
        logger.warning(
            "enfileiramento_mensagem_recebida_falhou",
            extra={
                "correlacao": correlacao,
                "empresa_id": str(mensagem.empresa_id),
                "mensagem_id": str(mensagem.pk),
            },
        )
        raise EnfileiramentoIndisponivel from erro
    Mensagem.objects.filter(
        pk=mensagem.pk,
        processamento_enfileirado=False,
        processamento_enfileirado_em=reivindicado_em,
    ).update(
        processamento_enfileirado=True,
        processamento_enfileirado_em=timezone.now(),
    )
    return True


def receber_webhook(
    *,
    empresa_id: UUID,
    token: str,
    payload: dict[str, Any],
    correlacao: str,
) -> ResultadoRecebimento:
    """Valida, normaliza, persiste e agenda uma mensagem sem duplicidade."""
    empresa = validar_webhook(empresa_id=empresa_id, token=token)
    mensagem, criado = _registrar_evento(
        empresa=empresa,
        payload=payload,
        correlacao=correlacao,
    )
    if mensagem is None:
        return ResultadoRecebimento(
            criado=False,
            mensagem_id=None,
            enfileirado=False,
        )
    enfileirado = _enfileirar(mensagem, correlacao)
    return ResultadoRecebimento(
        criado=criado,
        mensagem_id=mensagem.pk,
        enfileirado=enfileirado,
    )
