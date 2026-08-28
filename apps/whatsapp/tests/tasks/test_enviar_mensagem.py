"""Testes da politica Celery de retentativas de envio."""

from unittest.mock import patch

import pytest

from apps.atendimento.models import Mensagem
from apps.atendimento.tests.factories import MensagemFactory
from apps.auditoria.models import EventoAuditoria
from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    LimiteWhatsAppExcedido,
    WhatsAppIndisponivel,
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "erro",
    [WhatsAppIndisponivel("timeout"), LimiteWhatsAppExcedido("429")],
)
def test_task_tenta_cinco_vezes_e_persiste_falha_final_sanitizada(
    erro: Exception,
) -> None:
    """Falha se indisponibilidade exceder cinco chamadas ou vazar detalhe externo."""
    from apps.whatsapp.tasks.enviar_mensagem import enviar_mensagem_whatsapp

    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.PENDENTE,
    )
    with patch(
        "apps.whatsapp.services.enviar_mensagem.obter_provider",
        side_effect=erro,
    ) as obter:
        resultado = enviar_mensagem_whatsapp.apply(
            args=(str(mensagem.id), "corr-retry"),
            throw=False,
        )

    mensagem.refresh_from_db()
    assert resultado.failed()
    assert obter.call_count == 5
    assert mensagem.status == Mensagem.Status.FALHA
    assert mensagem.erro_sanitizado in {
        "whatsapp_indisponivel",
        "limite_whatsapp_excedido",
    }
    assert "timeout" not in mensagem.erro_sanitizado
    historico = EventoAuditoria.objects.filter(objeto_id=str(mensagem.id))
    assert historico.count() == 5
    assert set(historico.values_list("origem", flat=True)) == {
        "task_tentativa_whatsapp",
        "task_envio_whatsapp",
    }
    assert all(mensagem.texto not in str(evento.depois) for evento in historico)


@pytest.mark.django_db(transaction=True)
def test_task_nao_repete_credencial_invalida() -> None:
    """Falha se uma recusa permanente de configuracao consumir retentativas."""
    from apps.whatsapp.tasks.enviar_mensagem import enviar_mensagem_whatsapp

    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.PENDENTE,
    )
    with patch(
        "apps.whatsapp.services.enviar_mensagem.obter_provider",
        side_effect=CredencialWhatsAppInvalida("segredo recusado"),
    ) as obter:
        resultado = enviar_mensagem_whatsapp.apply(
            args=(str(mensagem.id), "corr-permanente"),
            throw=False,
        )

    mensagem.refresh_from_db()
    assert resultado.successful()
    assert resultado.result is False
    assert obter.call_count == 1
    assert mensagem.status == Mensagem.Status.FALHA
    assert mensagem.erro_sanitizado == "credencial_whatsapp_invalida"
