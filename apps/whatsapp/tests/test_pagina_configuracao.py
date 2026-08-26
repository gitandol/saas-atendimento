"""Testes da pagina-shell de conexao do WhatsApp."""

import pytest
from django.test import Client

from apps.contas.models import Usuario


@pytest.mark.django_db
def test_pagina_whatsapp_exige_autenticacao() -> None:
    """Protege a configuracao Evolution por sessao Django."""
    resposta = Client().get("/whatsapp/configuracao/")

    assert resposta.status_code == 302


@pytest.mark.django_db
def test_pagina_shell_consume_api_exibe_ajuda_e_confirma_acoes() -> None:
    """Renderiza controles HTMX, ajuda e confirmacoes sem regra na view."""
    usuario = Usuario.objects.create_user(email="pagina-whatsapp@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/whatsapp/configuracao/")

    assert resposta.status_code == 200
    assert b'hx-get="/api/v1/whatsapp/configuracao"' in resposta.content
    assert b'hx-put="/api/v1/whatsapp/configuracao"' in resposta.content
    assert b'hx-get="/api/v1/whatsapp/qrcode"' in resposta.content
    assert b'hx-get="/api/v1/whatsapp/estado"' in resposta.content
    assert b'hx-post="/api/v1/whatsapp/conectar"' in resposta.content
    assert b'hx-post="/api/v1/whatsapp/desconectar"' in resposta.content
    assert resposta.content.count(b"hx-confirm=") >= 2
    assert b'id="qrcode-whatsapp"' in resposta.content
    assert b"setTimeout" in resposta.content
    assert b"/ajuda/conexao-do-whatsapp/" in resposta.content
    assert b"Ajuda" in resposta.content


@pytest.mark.django_db
def test_sidebar_exibe_acesso_ao_whatsapp() -> None:
    """Mantem a conexao WhatsApp acessivel na navegacao autenticada."""
    usuario = Usuario.objects.create_user(email="sidebar-whatsapp@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/perfil/")

    assert b'href="/whatsapp/configuracao/"' in resposta.content
    assert b">WhatsApp<" in resposta.content
