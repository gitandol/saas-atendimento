"""Testes da pagina-shell da caixa de entrada."""

import ast
from pathlib import Path

import pytest
from django.test import Client

from apps.atendimento.models import Mensagem
from apps.atendimento.tests.factories import (
    ConversaFactory,
    MensagemFactory,
    UsuarioFactory,
)
from apps.empresas.models import MembroEmpresa


def _cliente(empresa):
    """Autentica um atendente ativo para renderizar a pagina."""
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
def test_pagina_caixa_exige_autenticacao() -> None:
    """Falha se a caixa operacional aceitar visitante anonimo."""
    assert Client().get("/atendimento/caixa-de-entrada/").status_code == 302


@pytest.mark.django_db
def test_pagina_shell_tem_tres_areas_htmx_estados_e_ajuda() -> None:
    """Falha se a interface perder estrutura, acessibilidade ou endpoints."""
    conversa = ConversaFactory()
    resposta = _cliente(conversa.empresa).get("/atendimento/caixa-de-entrada/")

    assert resposta.status_code == 200
    conteudo = resposta.content
    assert b'hx-get="/api/v1/atendimento/conversas"' in conteudo
    assert b'hx-trigger="load, every 3s"' in conteudo
    assert b'id="lista-conversas"' in conteudo
    assert b'id="historico-conversa"' in conteudo
    assert b'id="detalhes-conversa"' in conteudo
    assert b'id="formulario-resposta-manual"' in conteudo
    assert b'id="acoes-conversa"' in conteudo
    assert b'data-acao-conversa="assumir"' in conteudo
    assert b'data-acao-conversa="devolver-para-ia"' in conteudo
    assert b'data-acao-conversa="finalizar"' in conteudo
    assert b'data-acao-conversa="reabrir"' in conteudo
    assert b'maxlength="4096"' in conteudo
    assert b'role="status"' in conteudo
    assert b'aria-live="polite"' in conteudo
    assert b'id="erro-caixa"' in conteudo
    assert b'role="alert"' in conteudo
    assert b"/ajuda/caixa-de-entrada/" in conteudo
    assert b"caixa_entrada.js" in conteudo


@pytest.mark.django_db
def test_endpoints_htmx_renderizam_parciais_sem_duplicar_contrato() -> None:
    """Falha se HTMX receber JSON bruto em vez das regioes acessiveis."""
    conversa = ConversaFactory(contagem_nao_lida=1)
    mensagem = MensagemFactory(
        conversa=conversa,
        empresa=conversa.empresa,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.ATENDENTE,
        status=Mensagem.Status.FALHA,
    )
    cliente = _cliente(conversa.empresa)

    lista = cliente.get(
        "/api/v1/atendimento/conversas",
        HTTP_HX_REQUEST="true",
    )
    historico = cliente.get(
        f"/api/v1/atendimento/conversas/{conversa.id}/mensagens",
        HTTP_HX_REQUEST="true",
    )

    assert lista.status_code == 200
    assert b'data-conversa-id="' + str(conversa.id).encode() + b'"' in lista.content
    assert b"data-abrir-conversa" in lista.content
    assert historico.status_code == 200
    assert b'data-mensagem-id="' + str(mensagem.id).encode() + b'"' in historico.content
    assert b"/api/v1/whatsapp/mensagens/" in historico.content
    assert b"Reenviar" in historico.content


def test_view_da_caixa_nao_importa_models_ou_services() -> None:
    """Falha se a pagina-shell consultar negocio fora da API."""
    arquivo = Path("apps/atendimento/views/paginas/caixa_entrada.py")
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    importacoes = {
        no.module
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module
    }
    assert not {
        modulo for modulo in importacoes if ".models" in modulo or ".services" in modulo
    }
