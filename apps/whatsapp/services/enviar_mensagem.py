"""Envia e reabre mensagens de saida com idempotencia e auditoria."""

import logging
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.atendimento.models import Mensagem
from apps.atendimento.services.mensagens import mensagem_para_dto, snapshot_mensagem
from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa
from apps.empresas.services.obter_empresa import autorizar_membro
from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    InstanciaWhatsAppNaoEncontrada,
    LimiteWhatsAppExcedido,
    RequisicaoWhatsAppInvalida,
    WhatsAppIndisponivel,
)
from apps.whatsapp.services.configurar_instancia import (
    _obter_provider as obter_provider,
)

logger = logging.getLogger(__name__)
FALHAS_PERMANENTES = (
    CredencialWhatsAppInvalida,
    InstanciaWhatsAppNaoEncontrada,
    RequisicaoWhatsAppInvalida,
)
FALHAS_TRANSITORIAS = (LimiteWhatsAppExcedido, WhatsAppIndisponivel)


class ReenvioMensagemNaoPermitido(Exception):
    """Indica que a mensagem nao pertence ao tenant ou nao esta em falha."""


def _codigo_erro(erro: Exception) -> str:
    """Converte excecoes externas em codigos estaveis sem detalhes sensiveis."""
    codigos = {
        CredencialWhatsAppInvalida: "credencial_whatsapp_invalida",
        InstanciaWhatsAppNaoEncontrada: "instancia_whatsapp_nao_encontrada",
        LimiteWhatsAppExcedido: "limite_whatsapp_excedido",
        RequisicaoWhatsAppInvalida: "requisicao_whatsapp_invalida",
        WhatsAppIndisponivel: "whatsapp_indisponivel",
    }
    return codigos.get(type(erro), "falha_envio_whatsapp")


def _auditar(
    *,
    mensagem: Mensagem,
    antes: dict[str, object],
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> None:
    """Registra somente metadados de entrega, nunca o texto da mensagem."""
    depois = snapshot_mensagem(mensagem)
    registrar_alteracao(
        empresa=mensagem.empresa,
        objeto=mensagem,
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


def solicitar_envio(mensagem_id: UUID | str, correlacao: str) -> None:
    """Publica a task usando somente identificadores serializaveis."""
    from apps.whatsapp.tasks.enviar_mensagem import enviar_mensagem_whatsapp

    enviar_mensagem_whatsapp.delay(str(mensagem_id), correlacao)


@transaction.atomic
def executar_envio(*, mensagem_id: UUID, correlacao: str) -> bool:
    """Envia uma saida pendente uma vez sob bloqueio transacional."""
    mensagem = (
        Mensagem.objects.select_for_update()
        .select_related("empresa", "conversa__contato")
        .filter(pk=mensagem_id)
        .first()
    )
    if (
        mensagem is None
        or mensagem.direcao != Mensagem.Direcao.SAIDA
        or mensagem.status != Mensagem.Status.PENDENTE
    ):
        return False
    try:
        identificador = obter_provider(mensagem.empresa).enviar_texto(
            mensagem.conversa.contato.numero_normalizado,
            mensagem.texto,
            str(mensagem.id),
        )
    except FALHAS_PERMANENTES as erro:
        _marcar_falha_bloqueada(
            mensagem=mensagem,
            codigo=_codigo_erro(erro),
            correlacao=correlacao,
        )
        return False
    antes = snapshot_mensagem(mensagem)
    mensagem.status = Mensagem.Status.ENVIADA
    mensagem.identificador_externo = identificador
    mensagem.erro_sanitizado = ""
    mensagem.enviado_em = timezone.now()
    mensagem.save(
        update_fields=(
            "status",
            "identificador_externo",
            "erro_sanitizado",
            "enviado_em",
            "atualizado_em",
        )
    )
    _auditar(
        mensagem=mensagem,
        antes=antes,
        ator=None,
        origem="task_envio_whatsapp",
        correlacao=correlacao,
    )
    logger.info(
        "envio_whatsapp_concluido",
        extra={
            "empresa_id": str(mensagem.empresa_id),
            "mensagem_id": str(mensagem.id),
            "correlacao": correlacao,
            "metrica": "whatsapp_envios_total",
            "resultado": "enviada",
        },
    )
    return True


def _marcar_falha_bloqueada(
    *, mensagem: Mensagem, codigo: str, correlacao: str
) -> bool:
    """Persiste a falha de uma mensagem ja bloqueada pela transacao."""
    if mensagem.status != Mensagem.Status.PENDENTE:
        return False
    antes = snapshot_mensagem(mensagem)
    mensagem.status = Mensagem.Status.FALHA
    mensagem.erro_sanitizado = codigo
    mensagem.save(update_fields=("status", "erro_sanitizado", "atualizado_em"))
    _auditar(
        mensagem=mensagem,
        antes=antes,
        ator=None,
        origem="task_envio_whatsapp",
        correlacao=correlacao,
    )
    logger.warning(
        "envio_whatsapp_falhou",
        extra={
            "empresa_id": str(mensagem.empresa_id),
            "mensagem_id": str(mensagem.id),
            "correlacao": correlacao,
            "erro": codigo,
            "metrica": "whatsapp_envios_total",
            "resultado": "falha",
        },
    )
    return True


@transaction.atomic
def registrar_falha_final(
    *, mensagem_id: UUID, erro: Exception, correlacao: str
) -> bool:
    """Consolida a ultima tentativa transitoria em falha sanitizada."""
    mensagem = (
        Mensagem.objects.select_for_update()
        .select_related("empresa")
        .filter(pk=mensagem_id)
        .first()
    )
    if mensagem is None:
        return False
    return _marcar_falha_bloqueada(
        mensagem=mensagem,
        codigo=_codigo_erro(erro),
        correlacao=correlacao,
    )


@transaction.atomic
def registrar_tentativa_transitoria(*, mensagem_id: UUID, correlacao: str) -> bool:
    """Acrescenta uma revisao segura sem antecipar o estado final de falha."""
    mensagem = (
        Mensagem.objects.select_for_update()
        .select_related("empresa")
        .filter(
            pk=mensagem_id,
            direcao=Mensagem.Direcao.SAIDA,
            status=Mensagem.Status.PENDENTE,
        )
        .first()
    )
    if mensagem is None:
        return False
    snapshot = snapshot_mensagem(mensagem)
    registrar_alteracao(
        empresa=mensagem.empresa,
        objeto=mensagem,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=snapshot,
        depois=snapshot,
        campos_alterados=[],
        ator=None,
        origem="task_tentativa_whatsapp",
        correlacao=correlacao,
    )
    return True


def reenviar_mensagem(
    *,
    empresa: Empresa,
    ator: Usuario,
    mensagem_id: UUID,
    correlacao: str,
):
    """Reabre uma falha do tenant, audita e agenda a mesma entidade."""
    try:
        autorizar_membro(empresa=empresa, ator=ator)
    except PermissionDenied:
        raise
    with transaction.atomic():
        mensagem = (
            Mensagem.objects.select_for_update()
            .select_related("empresa")
            .filter(
                pk=mensagem_id,
                empresa=empresa,
                direcao=Mensagem.Direcao.SAIDA,
                status=Mensagem.Status.FALHA,
            )
            .first()
        )
        if mensagem is None:
            raise ReenvioMensagemNaoPermitido
        antes = snapshot_mensagem(mensagem)
        mensagem.status = Mensagem.Status.PENDENTE
        mensagem.erro_sanitizado = ""
        mensagem.save(update_fields=("status", "erro_sanitizado", "atualizado_em"))
        _auditar(
            mensagem=mensagem,
            antes=antes,
            ator=ator,
            origem="api_reenvio_whatsapp",
            correlacao=correlacao,
        )
        resultado = mensagem_para_dto(mensagem)
    solicitar_envio(mensagem.id, correlacao)
    logger.info(
        "reenvio_whatsapp_solicitado",
        extra={
            "empresa_id": str(empresa.id),
            "mensagem_id": str(mensagem.id),
            "correlacao": correlacao,
            "metrica": "whatsapp_reenvios_manuais_total",
        },
    )
    return resultado
