"""Aplica recibos de entrega com transicoes validas e idempotentes."""

import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.atendimento.models import Mensagem
from apps.atendimento.services.mensagens import snapshot_mensagem
from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.empresas.models import Empresa

logger = logging.getLogger(__name__)
TRANSICOES_VALIDAS = {
    Mensagem.Status.PENDENTE: {Mensagem.Status.ENVIADA, Mensagem.Status.FALHA},
    Mensagem.Status.ENVIADA: {Mensagem.Status.ENTREGUE, Mensagem.Status.FALHA},
}


@transaction.atomic
def atualizar_status_entrega(
    *,
    empresa: Empresa,
    identificador_externo: str,
    status: str,
    ocorrido_em: datetime | None,
    correlacao: str,
) -> bool:
    """Atualiza uma saida do tenant uma vez quando a transicao e permitida."""
    mensagem = (
        Mensagem.objects.select_for_update()
        .select_related("empresa")
        .filter(
            empresa=empresa,
            direcao=Mensagem.Direcao.SAIDA,
            identificador_externo=identificador_externo,
        )
        .first()
    )
    if mensagem is None or mensagem.status == status:
        return False
    if status not in TRANSICOES_VALIDAS.get(mensagem.status, set()):
        logger.info(
            "recibo_whatsapp_transicao_ignorada",
            extra={
                "empresa_id": str(empresa.id),
                "mensagem_id": str(mensagem.id),
                "correlacao": correlacao,
                "status_atual": mensagem.status,
                "status_recebido": status,
            },
        )
        return False
    antes = snapshot_mensagem(mensagem)
    instante = ocorrido_em or timezone.now()
    mensagem.status = status
    if status == Mensagem.Status.ENVIADA and mensagem.enviado_em is None:
        mensagem.enviado_em = instante
    elif status == Mensagem.Status.ENTREGUE:
        mensagem.entregue_em = instante
    elif status == Mensagem.Status.FALHA:
        mensagem.erro_sanitizado = "falha_entrega_whatsapp"
    mensagem.save(
        update_fields=(
            "status",
            "erro_sanitizado",
            "enviado_em",
            "entregue_em",
            "atualizado_em",
        )
    )
    depois = snapshot_mensagem(mensagem)
    registrar_alteracao(
        empresa=empresa,
        objeto=mensagem,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        depois=depois,
        campos_alterados=[
            campo for campo, valor in depois.items() if antes.get(campo) != valor
        ],
        ator=None,
        origem="webhook_entrega_whatsapp",
        correlacao=correlacao,
    )
    logger.info(
        "recibo_whatsapp_aplicado",
        extra={
            "empresa_id": str(empresa.id),
            "mensagem_id": str(mensagem.id),
            "correlacao": correlacao,
            "status": status,
            "metrica": "whatsapp_recibos_total",
        },
    )
    return True
