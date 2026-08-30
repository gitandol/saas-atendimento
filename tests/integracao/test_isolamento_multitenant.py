"""Prova isolamento com identificadores externos repetidos entre empresas."""

from unittest.mock import patch
from uuid import UUID

import pytest
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.test import Client

from apps.atendimento.models import Mensagem
from apps.atendimento.services.consultas.obter_historico import obter_historico
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.whatsapp.models import ConfiguracaoWhatsApp
from apps.whatsapp.services.validar_webhook import (
    LimiteWebhookExcedido,
    gerar_token_webhook,
    limitar_webhook,
)


def _cliente(empresa: Empresa, indice: int) -> Client:
    """Cria uma sessao vinculada somente ao tenant informado."""
    usuario = Usuario.objects.create_user(email=f"isolamento-{indice}@example.com")
    MembroEmpresa.objects.create(
        empresa=empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    cliente = Client()
    cliente.force_login(usuario)
    return cliente


def _payload(identificador: str, indice: int) -> dict[str, object]:
    """Monta o mesmo identificador externo com remetentes sinteticos distintos."""
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": identificador,
                "remoteJid": f"55{'0' * 9}{indice}@s.whatsapp.net",
                "fromMe": False,
            },
            "pushName": f"Cliente {indice}",
            "message": {"conversation": f"entrada-{indice}"},
            "messageTimestamp": 1_725_192_000,
        },
    }


@pytest.mark.django_db
def test_identificador_externo_repetido_permanece_isolado() -> None:
    """Isola persistencia, API, service, cache e argumentos das tasks."""
    cache.clear()
    empresas = [
        Empresa.objects.create(
            id=UUID(f"00000000-0000-4000-8000-00000000000{indice}"),
            nome=f"Tenant {indice}",
        )
        for indice in (1, 2)
    ]
    for indice, empresa in enumerate(empresas, start=1):
        ConfiguracaoWhatsApp.objects.create(
            empresa=empresa,
            url_base="https://evolution.example.com",
            nome_instancia=f"tenant-{indice}",
            ativo=True,
        )
    identificador = "11111111-1111-4111-8111-111111111111"

    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as enfileirar:
        respostas = [
            Client().post(
                (
                    f"/api/v1/webhooks/evolution/{empresa.id}/"
                    f"{gerar_token_webhook(empresa_id=empresa.id)}/"
                ),
                data=_payload(identificador, indice),
                content_type="application/json",
            )
            for indice, empresa in enumerate(empresas, start=1)
        ]

    assert [resposta.status_code for resposta in respostas] == [200, 200]
    mensagens = list(
        Mensagem.objects.filter(identificador_externo=identificador).order_by(
            "empresa_id"
        )
    )
    assert len(mensagens) == 2
    assert {mensagem.empresa_id for mensagem in mensagens} == {
        empresa.id for empresa in empresas
    }
    assert enfileirar.call_count == 2
    for chamada, mensagem in zip(enfileirar.call_args_list, mensagens, strict=True):
        assert chamada.args[:2] == (
            str(mensagem.conversa_id),
            str(mensagem.id),
        )

    clientes = [_cliente(empresa, indice) for indice, empresa in enumerate(empresas)]
    for cliente, mensagem in zip(clientes, mensagens, strict=True):
        lista = cliente.get("/api/v1/atendimento/conversas").json()["conversas"]
        assert [item["id"] for item in lista] == [str(mensagem.conversa_id)]
    with pytest.raises(ObjectDoesNotExist):
        obter_historico(
            empresa=empresas[0],
            conversa_id=mensagens[1].conversa_id,
            cursor=None,
            depois_de=None,
            limite=10,
        )

    for empresa in empresas:
        for _ in range(60):
            limitar_webhook(empresa_id=empresa.id, origem="origem-compartilhada")
        with pytest.raises(LimiteWebhookExcedido):
            limitar_webhook(empresa_id=empresa.id, origem="origem-compartilhada")
