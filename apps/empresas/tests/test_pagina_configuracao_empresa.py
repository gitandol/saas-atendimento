"""Testes da pagina-shell de configuracao da empresa."""

import pytest
from django.test import Client

from apps.contas.models import Usuario


@pytest.mark.django_db
def test_pagina_exige_autenticacao() -> None:
    """Protege o formulario empresarial por sessao Django."""
    resposta = Client().get("/empresa/configuracao/")

    assert resposta.status_code == 302


@pytest.mark.django_db
def test_pagina_autenticada_consume_api_com_htmx_e_exibe_ajuda() -> None:
    """Renderiza somente o shell dinamico com feedback e ajuda contextual."""
    usuario = Usuario.objects.create_user(email="pagina-empresa@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/empresa/configuracao/")

    assert resposta.status_code == 200
    assert b"/static/vendor/htmx.min.js" in resposta.content
    assert b"/static/src/css/configuracao-empresa.css" in resposta.content
    assert b'hx-ext="json-enc"' in resposta.content
    assert b'hx-get="/api/v1/empresa"' in resposta.content
    assert b'hx-put="/api/v1/empresa"' in resposta.content
    assert b'id="feedback-configuracao"' in resposta.content
    assert b"/ajuda/configuracao-da-empresa/" in resposta.content
    assert b"Ajuda" in resposta.content


def test_assets_htmx_da_pagina_estao_disponiveis() -> None:
    """Garante que a tela nao dependa de scripts externos ou inexistentes."""
    from django.contrib.staticfiles import finders

    assert finders.find("vendor/htmx.min.js") is not None
    assert finders.find("vendor/htmx-ext-json-enc.js") is not None
    assert finders.find("src/css/configuracao-empresa.css") is not None
