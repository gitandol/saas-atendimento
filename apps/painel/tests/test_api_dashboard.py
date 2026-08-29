"""Testes HTTP das metricas do dashboard operacional."""

import ast
from pathlib import Path

import pytest
from django.core.cache import cache
from django.test import Client

from apps.atendimento.tests.factories import (
    ConversaFactory,
    EmpresaFactory,
    UsuarioFactory,
)
from apps.empresas.models import MembroEmpresa


def _cliente_membro(empresa) -> Client:
    """Autentica um membro ativo da empresa informada."""
    usuario = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    cliente = Client()
    cliente.force_login(usuario)
    return cliente


@pytest.mark.django_db
def test_api_metricas_exige_sessao() -> None:
    """Falha se o dashboard operacional aceitar acesso anonimo."""
    assert Client().get("/api/v1/painel/metricas").status_code == 401


@pytest.mark.django_db
def test_api_metricas_publica_contrato_e_isola_empresa() -> None:
    """Falha se a API omitir campos ou contar conversas de outro tenant."""
    cache.clear()
    empresa = EmpresaFactory()
    ConversaFactory(empresa=empresa, contato__empresa=empresa)
    ConversaFactory()
    cliente = _cliente_membro(empresa)

    resposta = cliente.get("/api/v1/painel/metricas")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "conversas_abertas": 1,
        "conversas_ia": 1,
        "conversas_humano": 0,
        "mensagens_recebidas_hoje": 0,
        "mensagens_enviadas_hoje": 0,
        "mensagens_com_falha": 0,
        "estado_openai": "INATIVA",
        "estado_evolution": "DESCONECTADO",
    }


@pytest.mark.django_db
def test_api_htmx_renderiza_alertas_acionaveis() -> None:
    """Falha se integracoes inativas nao levarem a configuracao correta."""
    cache.clear()
    empresa = EmpresaFactory()
    cliente = _cliente_membro(empresa)

    resposta = cliente.get(
        "/api/v1/painel/metricas",
        HTTP_HX_REQUEST="true",
    )

    assert resposta.status_code == 200
    assert b'data-alerta-integracao="openai"' in resposta.content
    assert b'href="/ia/configuracao/"' in resposta.content
    assert b'data-alerta-integracao="evolution"' in resposta.content
    assert b'href="/whatsapp/configuracao/"' in resposta.content
    assert b'data-metrica="conversas-abertas"' in resposta.content
    assert b">0<" in resposta.content


def test_endpoint_do_dashboard_nao_importa_models() -> None:
    """Falha se a fronteira HTTP consultar persistencia diretamente."""
    arquivo = Path("apps/painel/api/endpoints/dashboard.py")
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    importacoes = {
        no.module
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module
    }

    assert not {modulo for modulo in importacoes if ".models" in modulo}
