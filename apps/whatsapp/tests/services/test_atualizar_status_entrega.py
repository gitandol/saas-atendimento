"""Testes das transicoes e recibos de entrega do WhatsApp."""

from datetime import UTC, datetime

import pytest

from apps.atendimento.models import Mensagem
from apps.atendimento.tests.factories import MensagemFactory
from apps.auditoria.models import EventoAuditoria


@pytest.mark.django_db
def test_transiciona_enviada_para_entregue_e_ignora_recibo_repetido() -> None:
    """Falha se um recibo duplicado gerar nova revisao ou perder o instante."""
    from apps.whatsapp.services.atualizar_status_entrega import atualizar_status_entrega

    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.ENVIADA,
        identificador_externo="wamid-entrega-1",
    )
    ocorrido_em = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)

    primeiro = atualizar_status_entrega(
        empresa=mensagem.empresa,
        identificador_externo="wamid-entrega-1",
        status=Mensagem.Status.ENTREGUE,
        ocorrido_em=ocorrido_em,
        correlacao="corr-entrega",
    )
    quantidade_eventos = EventoAuditoria.objects.filter(
        objeto_id=str(mensagem.id)
    ).count()
    repetido = atualizar_status_entrega(
        empresa=mensagem.empresa,
        identificador_externo="wamid-entrega-1",
        status=Mensagem.Status.ENTREGUE,
        ocorrido_em=ocorrido_em,
        correlacao="corr-repetida",
    )

    mensagem.refresh_from_db()
    assert primeiro is True
    assert repetido is False
    assert mensagem.status == Mensagem.Status.ENTREGUE
    assert mensagem.entregue_em == ocorrido_em
    assert (
        EventoAuditoria.objects.filter(objeto_id=str(mensagem.id)).count()
        == quantidade_eventos
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status_inicial",
    [Mensagem.Status.PENDENTE, Mensagem.Status.ENVIADA],
)
def test_recibo_de_falha_e_valido_para_pendente_ou_enviada(
    status_inicial: str,
) -> None:
    """Falha se a transicao externa de falha deixar estado ambiguo no painel."""
    from apps.whatsapp.services.atualizar_status_entrega import atualizar_status_entrega

    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        status=status_inicial,
        identificador_externo=f"wamid-falha-{status_inicial}",
    )

    assert (
        atualizar_status_entrega(
            empresa=mensagem.empresa,
            identificador_externo=mensagem.identificador_externo,
            status=Mensagem.Status.FALHA,
            ocorrido_em=None,
            correlacao="corr-falha-recibo",
        )
        is True
    )
    mensagem.refresh_from_db()
    assert mensagem.status == Mensagem.Status.FALHA
    assert mensagem.erro_sanitizado == "falha_entrega_whatsapp"


def test_normaliza_recibo_de_entrega_sem_conteudo_da_mensagem() -> None:
    """Falha se o webhook nao reconhecer o identificador e estado de entrega."""
    from apps.whatsapp.services.normalizar_evento import normalizar_evento_entrega

    evento = normalizar_evento_entrega(
        {
            "event": "messages.update",
            "data": {
                "key": {"id": "wamid-recibo-1"},
                "status": "DELIVERY_ACK",
                "messageTimestamp": 1_725_192_000,
            },
        }
    )

    assert evento is not None
    assert evento.identificador_externo == "wamid-recibo-1"
    assert evento.status == Mensagem.Status.ENTREGUE
