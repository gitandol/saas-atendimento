"""Testes do contrato HTTP externo do webhook Evolution."""

import ast
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest
from django.test import Client

from apps.atendimento.models import Mensagem
from apps.empresas.models import Empresa
from apps.whatsapp.models import ConfiguracaoWhatsApp

EMPRESA_ID = UUID("11111111-1111-4111-8111-111111111111")
TOKEN_VALIDO = "e1b2edbc8a922faaeac082d8496bcb0b8bb55b8c47bf24ab10fd6b4afbe18003"
ROTA = f"/api/v1/webhooks/evolution/{EMPRESA_ID}/{TOKEN_VALIDO}/"


def _configuracao(*, ativa: bool = True) -> ConfiguracaoWhatsApp:
    """Cria configuracao coerente com o token literal de contrato."""
    empresa = Empresa.objects.create(id=EMPRESA_ID, nome="Empresa webhook HTTP")
    return ConfiguracaoWhatsApp.objects.create(
        empresa=empresa,
        url_base="https://evolution.example.com",
        nome_instancia="empresa-http",
        ativo=ativa,
    )


def _payload() -> dict[str, object]:
    """Monta uma entrada textual valida da Evolution."""
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": "http-mensagem-1",
                "remoteJid": "5568999994321@s.whatsapp.net",
                "fromMe": False,
            },
            "pushName": "Cliente HTTP",
            "message": {"conversation": "Mensagem externa"},
            "messageTimestamp": 1_725_192_000,
        },
    }


@pytest.mark.django_db
def test_endpoint_recusa_token_invalido_e_configuracao_inativa() -> None:
    """Autentica a URL e exige uma instancia operacional."""
    configuracao = _configuracao(ativa=False)
    invalido = Client().post(
        f"/api/v1/webhooks/evolution/{EMPRESA_ID}/token-invalido/",
        data=_payload(),
        content_type="application/json",
    )
    inativo = Client().post(ROTA, data=_payload(), content_type="application/json")

    assert invalido.status_code == 401
    assert invalido.json()["codigo"] == "webhook_nao_autorizado"
    assert inativo.status_code == 409
    assert inativo.json()["codigo"] == "whatsapp_inativo"
    assert not Mensagem.objects.filter(empresa=configuracao.empresa).exists()


@pytest.mark.django_db
def test_endpoint_recusa_tipo_json_invalido_e_payload_grande() -> None:
    """Limita trabalho e memoria antes de delegar ao dominio."""
    _configuracao()
    tipo = Client().post(ROTA, data="{}", content_type="text/plain")
    invalido = Client().post(ROTA, data="{", content_type="application/json")
    grande = Client().post(
        ROTA,
        data=json.dumps({"event": "messages.upsert", "lixo": "x" * 262_145}),
        content_type="application/json",
    )

    assert tipo.status_code == 415
    assert invalido.status_code == 400
    assert grande.status_code == 413


@pytest.mark.django_db
def test_endpoint_aceita_evento_desconhecido_e_midia_sem_criar_mensagem(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Confirma eventos nao suportados sem iniciar resposta automatica."""
    configuracao = _configuracao()
    desconhecido = Client().post(
        ROTA,
        data={"event": "connection.update", "data": {}},
        content_type="application/json",
    )
    midia_payload = _payload()
    dados = midia_payload["data"]
    assert isinstance(dados, dict)
    dados["message"] = {"imageMessage": {"caption": "segredo"}}
    midia = Client().post(
        ROTA,
        data=midia_payload,
        content_type="application/json",
    )

    assert desconhecido.status_code == 200
    assert desconhecido.json()["status"] == "ignorado"
    assert midia.status_code == 200
    assert midia.json()["status"] == "ignorado"
    assert not Mensagem.objects.filter(empresa=configuracao.empresa).exists()
    assert "segredo" not in caplog.text


@pytest.mark.django_db
def test_endpoint_persiste_e_reconhece_repeticao_com_correlacao() -> None:
    """Publica contrato 200 idempotente e a correlacao sem expor conteudo."""
    _configuracao()
    with patch(
        "apps.whatsapp.services.receber_webhook.processar_mensagem_recebida.delay"
    ):
        primeira = Client().post(
            ROTA,
            data=_payload(),
            content_type="application/json",
            HTTP_X_CORRELATION_ID="corr-http",
        )
        repetida = Client().post(
            ROTA,
            data=_payload(),
            content_type="application/json",
            HTTP_X_CORRELATION_ID="corr-http-2",
        )

    assert primeira.status_code == 200
    assert primeira.json()["status"] == "recebido"
    assert repetida.status_code == 200
    assert repetida.json()["status"] == "duplicado"
    assert primeira.headers["X-Correlation-ID"] == "corr-http"
    assert Mensagem.objects.filter(identificador_externo="http-mensagem-1").count() == 1


def test_endpoint_nao_importa_models_nem_tasks() -> None:
    """Mantem persistencia e Celery atras do service de recebimento."""
    arquivo = Path("apps/whatsapp/api/endpoints/webhook_evolution.py")
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    importacoes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and no.module:
            importacoes.add(no.module)
        elif isinstance(no, ast.Import):
            importacoes.update(alias.name for alias in no.names)

    assert not {
        modulo for modulo in importacoes if ".models" in modulo or ".tasks" in modulo
    }
