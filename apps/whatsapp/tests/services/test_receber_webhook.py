"""Testes transacionais do recebimento de webhooks Evolution."""

from datetime import timedelta
from unittest.mock import patch
from uuid import UUID

import pytest
from django.utils import timezone

from apps.atendimento.models import Contato, Conversa, Mensagem
from apps.empresas.models import Empresa
from apps.whatsapp.models import ConfiguracaoWhatsApp

EMPRESA_ID = UUID("11111111-1111-4111-8111-111111111111")
TOKEN_VALIDO = "e1b2edbc8a922faaeac082d8496bcb0b8bb55b8c47bf24ab10fd6b4afbe18003"


def _configuracao(*, ativa: bool = True) -> ConfiguracaoWhatsApp:
    """Cria a empresa fixa usada pela fixture HMAC independente."""
    empresa = Empresa.objects.create(id=EMPRESA_ID, nome="Empresa webhook")
    return ConfiguracaoWhatsApp.objects.create(
        empresa=empresa,
        url_base="https://evolution.example.com",
        nome_instancia="empresa-webhook",
        ativo=ativa,
    )


def _payload(
    *,
    identificador: str = "mensagem-1",
    from_me: bool = False,
    remote_jid: str = "5568999991234@s.whatsapp.net",
):
    """Monta uma mensagem textual realista da Evolution."""
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": identificador,
                "remoteJid": remote_jid,
                "fromMe": from_me,
            },
            "pushName": "Cliente",
            "message": {"conversation": "Ola, preciso de ajuda"},
            "messageTimestamp": 1_725_192_000,
        },
    }


@pytest.mark.django_db
def test_valida_token_e_configuracao_ativa() -> None:
    """Recusa segredo incorreto e instancia desativada antes de persistir."""
    from apps.whatsapp.services.validar_webhook import (
        ConfiguracaoWebhookInativa,
        TokenWebhookInvalido,
        validar_webhook,
    )

    configuracao = _configuracao(ativa=False)
    with pytest.raises(TokenWebhookInvalido):
        validar_webhook(empresa_id=EMPRESA_ID, token="invalido")
    with pytest.raises(ConfiguracaoWebhookInativa):
        validar_webhook(empresa_id=EMPRESA_ID, token=TOKEN_VALIDO)

    configuracao.ativo = True
    configuracao.save(update_fields=("ativo", "atualizado_em"))
    assert (
        validar_webhook(empresa_id=EMPRESA_ID, token=TOKEN_VALIDO)
        == configuracao.empresa
    )


@pytest.mark.django_db
def test_persiste_entrada_uma_vez_e_enfileira_uma_vez() -> None:
    """Impede duplicacao de agregado, auditoria e publicacao Celery."""
    from apps.whatsapp.services.receber_webhook import receber_webhook

    configuracao = _configuracao()
    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as delay:
        primeiro = receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(),
            correlacao="corr-entrada",
        )
        repetido = receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(),
            correlacao="corr-repetida",
        )

    assert primeiro.criado is True
    assert repetido.criado is False
    assert primeiro.mensagem_id == repetido.mensagem_id
    assert Contato.objects.filter(empresa=configuracao.empresa).count() == 1
    assert Conversa.objects.filter(empresa=configuracao.empresa).count() == 1
    assert Mensagem.objects.filter(empresa=configuracao.empresa).count() == 1
    delay.assert_called_once_with(
        str(Mensagem.objects.get(pk=primeiro.mensagem_id).conversa_id),
        str(primeiro.mensagem_id),
        "corr-entrada",
    )


@pytest.mark.django_db
def test_saida_da_instancia_e_persistida_sem_enfileirar_resposta() -> None:
    """Registra autoria local sem criar ciclo de resposta automatica."""
    from apps.whatsapp.services.receber_webhook import receber_webhook

    configuracao = _configuracao()
    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as delay:
        resultado = receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(identificador="saida-1", from_me=True),
            correlacao="corr-saida",
        )

    mensagem = Mensagem.objects.get(pk=resultado.mensagem_id)
    assert mensagem.empresa == configuracao.empresa
    assert mensagem.direcao == Mensagem.Direcao.SAIDA
    assert mensagem.autor == Mensagem.Autor.SISTEMA
    assert mensagem.status == Mensagem.Status.ENVIADA
    delay.assert_not_called()


@pytest.mark.django_db
def test_grupo_nao_cria_atendimento_nem_enfileira_resposta() -> None:
    """Mantem mensagens de grupo fora do dominio de atendimento direto."""
    from apps.whatsapp.services.receber_webhook import receber_webhook

    configuracao = _configuracao()
    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as delay:
        resultado = receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(remote_jid="120363123456789012@g.us"),
            correlacao="corr-grupo",
        )

    assert resultado.criado is False
    assert resultado.mensagem_id is None
    assert resultado.enfileirado is False
    assert Contato.objects.filter(empresa=configuracao.empresa).count() == 0
    assert Conversa.objects.filter(empresa=configuracao.empresa).count() == 0
    assert Mensagem.objects.filter(empresa=configuracao.empresa).count() == 0
    delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_falha_do_broker_preserva_mensagem_e_retry_enfileira_uma_vez() -> None:
    """Permite repetir o webhook apos falha de publicacao sem duplicar dados."""
    from apps.whatsapp.services.receber_webhook import (
        EnfileiramentoIndisponivel,
        receber_webhook,
    )

    configuracao = _configuracao()
    with (
        patch(
            "apps.whatsapp.services.receber_webhook.responder_conversa.delay",
            side_effect=RuntimeError("broker indisponivel"),
        ),
        pytest.raises(EnfileiramentoIndisponivel),
    ):
        receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(identificador="retry-1"),
            correlacao="corr-falha",
        )

    assert (
        Mensagem.objects.filter(
            empresa=configuracao.empresa,
            identificador_externo="retry-1",
        ).count()
        == 1
    )

    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as delay:
        resultado = receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(identificador="retry-1"),
            correlacao="corr-retry",
        )
        receber_webhook(
            empresa_id=EMPRESA_ID,
            token=TOKEN_VALIDO,
            payload=_payload(identificador="retry-1"),
            correlacao="corr-duplicada",
        )

    assert resultado.criado is False
    delay.assert_called_once_with(
        str(Mensagem.objects.get(pk=resultado.mensagem_id).conversa_id),
        str(resultado.mensagem_id),
        "corr-retry",
    )


@pytest.mark.django_db
def test_leituras_concorrentes_reivindicam_uma_unica_publicacao() -> None:
    """Usa o banco para impedir duas tasks a partir de estados obsoletos."""
    from apps.atendimento.tests.factories import MensagemFactory
    from apps.whatsapp.services.receber_webhook import _enfileirar

    criada = MensagemFactory()
    primeira_leitura = Mensagem.objects.get(pk=criada.pk)
    segunda_leitura = Mensagem.objects.get(pk=criada.pk)

    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as delay:
        primeiro = _enfileirar(primeira_leitura, "corr-concorrente-1")
        segundo = _enfileirar(segunda_leitura, "corr-concorrente-2")

    assert primeiro is True
    assert segundo is False
    delay.assert_called_once_with(
        str(criada.conversa_id), str(criada.pk), "corr-concorrente-1"
    )


@pytest.mark.django_db
def test_reivindicacao_abandonada_pode_ser_publicada_novamente() -> None:
    """Recupera queda do processo entre a reivindicacao e o broker."""
    from apps.atendimento.tests.factories import MensagemFactory
    from apps.whatsapp.services.receber_webhook import _enfileirar

    mensagem = MensagemFactory(
        processamento_enfileirado_em=timezone.now() - timedelta(minutes=10)
    )

    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as delay:
        enfileirado = _enfileirar(mensagem, "corr-lease-expirado")

    assert enfileirado is True
    delay.assert_called_once_with(
        str(mensagem.conversa_id), str(mensagem.pk), "corr-lease-expirado"
    )


@pytest.mark.django_db
def test_recibo_de_entrega_atualiza_saida_uma_vez_sem_criar_mensagem() -> None:
    """Falha se webhook repetido duplicar mensagem ou historico de entrega."""
    from apps.atendimento.tests.factories import MensagemFactory
    from apps.auditoria.models import EventoAuditoria
    from apps.whatsapp.services.receber_webhook import receber_webhook

    configuracao = _configuracao()
    mensagem = MensagemFactory(
        empresa=configuracao.empresa,
        conversa__empresa=configuracao.empresa,
        conversa__contato__empresa=configuracao.empresa,
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.ENVIADA,
        identificador_externo="wamid-webhook-entrega",
    )
    payload = {
        "event": "messages.update",
        "data": {
            "key": {"id": "wamid-webhook-entrega"},
            "status": "DELIVERY_ACK",
            "messageTimestamp": 1_725_192_000,
        },
    }

    primeiro = receber_webhook(
        empresa_id=EMPRESA_ID,
        token=TOKEN_VALIDO,
        payload=payload,
        correlacao="corr-recibo",
    )
    eventos = EventoAuditoria.objects.filter(objeto_id=str(mensagem.id)).count()
    repetido = receber_webhook(
        empresa_id=EMPRESA_ID,
        token=TOKEN_VALIDO,
        payload=payload,
        correlacao="corr-recibo-repetido",
    )

    mensagem.refresh_from_db()
    assert primeiro.mensagem_id == mensagem.id
    assert repetido.mensagem_id == mensagem.id
    assert mensagem.status == Mensagem.Status.ENTREGUE
    assert Mensagem.objects.filter(empresa=configuracao.empresa).count() == 1
    assert EventoAuditoria.objects.filter(objeto_id=str(mensagem.id)).count() == eventos
