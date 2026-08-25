"""Testes da pagina-shell de configuracao da IA."""

import pytest
from django.test import Client

from apps.contas.models import Usuario


@pytest.mark.django_db
def test_pagina_de_ia_exige_autenticacao() -> None:
    """Protege a configuracao de IA por sessao Django."""
    resposta = Client().get("/ia/configuracao/")

    assert resposta.status_code == 302


@pytest.mark.django_db
def test_pagina_shell_consume_api_e_exibe_ajuda() -> None:
    """Renderiza controles dinamicos sem consultar models na view."""
    usuario = Usuario.objects.create_user(email="pagina-ia@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/ia/configuracao/")

    assert resposta.status_code == 200
    assert b"/static/vendor/htmx.min.js" in resposta.content
    assert b'hx-get="/api/v1/ia/configuracao"' in resposta.content
    assert b'hx-put="/api/v1/ia/configuracao"' in resposta.content
    assert b'hx-post="/api/v1/ia/teste"' in resposta.content
    assert b'hx-delete="/api/v1/ia/configuracao/chave"' in resposta.content
    assert b'type="password"' in resposta.content
    assert b'name="chave_api"' in resposta.content
    assert b'id="feedback-ia"' in resposta.content
    assert b"/ajuda/configuracao-de-ia/" in resposta.content
    assert b"Ajuda" in resposta.content


@pytest.mark.django_db
def test_pagina_alinha_checkbox_de_respostas_automaticas() -> None:
    """Agrupa o checkbox e seu texto na mesma linha visual."""
    usuario = Usuario.objects.create_user(email="checkbox-ia@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/ia/configuracao/")

    assert resposta.status_code == 200
    assert b'<label class="campo-checkbox">' in resposta.content
    assert b'name="respostas_automaticas_ativas" type="checkbox"' in resposta.content


@pytest.mark.django_db
def test_pagina_separa_cartoes_de_configuracao_e_acoes() -> None:
    """Organiza os cartoes da pagina em uma pilha com espacamento."""
    usuario = Usuario.objects.create_user(email="cartoes-ia@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/ia/configuracao/")

    assert resposta.status_code == 200
    assert b'id="carregador-ia" class="pilha-configuracao"' in resposta.content


@pytest.mark.django_db
def test_sidebar_exibe_acesso_a_configuracao_de_ia() -> None:
    """Mantem a nova pagina acessivel na navegacao autenticada."""
    usuario = Usuario.objects.create_user(email="sidebar-ia@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/perfil/")

    assert b'href="/ia/configuracao/"' in resposta.content
    assert b">IA<" in resposta.content
