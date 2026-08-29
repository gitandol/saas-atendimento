"""Testes da pagina-shell do dashboard operacional."""

import ast
from pathlib import Path

import pytest
from django.test import Client

from apps.atendimento.tests.factories import EmpresaFactory, UsuarioFactory
from apps.empresas.models import MembroEmpresa


def _cliente_membro(empresa) -> Client:
    """Autentica um membro para acessar a pagina protegida."""
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
def test_pagina_dashboard_exige_autenticacao() -> None:
    """Falha se a pagina operacional aceitar visitante anonimo."""
    assert Client().get("/painel/").status_code == 302


@pytest.mark.django_db
def test_pagina_dashboard_tem_htmx_estados_ajuda_e_navegacao() -> None:
    """Falha se a shell perder atualizacao, feedback ou acesso contextual."""
    empresa = EmpresaFactory()
    resposta = _cliente_membro(empresa).get("/painel/")

    assert resposta.status_code == 200
    conteudo = resposta.content
    assert b'hx-get="/api/v1/painel/metricas"' in conteudo
    assert b'hx-trigger="load, every 30s"' in conteudo
    assert b'id="metricas-dashboard"' in conteudo
    assert b'aria-live="polite"' in conteudo
    assert b'role="status"' in conteudo
    assert b'id="erro-dashboard"' in conteudo
    assert b'role="alert"' in conteudo
    assert b"/ajuda/dashboard/" in conteudo
    assert b'href="/painel/"' in conteudo
    assert b"dashboard.css" in conteudo


def test_view_do_dashboard_nao_importa_models_ou_services() -> None:
    """Falha se a pagina-shell acessar qualquer regra de negocio."""
    arquivo = Path("apps/painel/views/paginas/dashboard.py")
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    importacoes = {
        no.module
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module
    }

    assert not {
        modulo for modulo in importacoes if ".models" in modulo or ".services" in modulo
    }
