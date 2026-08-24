"""Testes das paginas-shell de contas."""

from unittest.mock import patch

import pytest
from django.test import Client, RequestFactory


@pytest.mark.django_db
def test_pagina_de_login_renderiza_shell_publico() -> None:
    """Disponibiliza shell que envia credenciais pela API versionada."""
    resposta = Client().get("/entrar/")

    assert resposta.status_code == 200
    assert "contas/autenticacao/login.html" in [
        template.name for template in resposta.templates
    ]
    assert b"/api/v1/autenticacao/login" in resposta.content
    assert b"/api/v1/autenticacao/csrf" in resposta.content


@pytest.mark.django_db
def test_pagina_de_perfil_renderiza_shell_da_api() -> None:
    """Disponibiliza shell cujo conteudo dinamico vem da API versionada."""
    resposta = Client().get("/perfil/")

    assert resposta.status_code == 200
    assert "contas/perfil.html" in [template.name for template in resposta.templates]
    assert b"/api/v1/perfil" in resposta.content


def test_views_de_paginas_apenas_delegam_ao_render() -> None:
    """Evita consultas ou regras de negocio na camada de paginas."""
    from apps.contas.views.paginas.autenticacao import pagina_login
    from apps.contas.views.paginas.perfil import pagina_perfil

    requisicao = RequestFactory().get("/")
    with patch("apps.contas.views.paginas.autenticacao.render") as render_login:
        pagina_login(requisicao)
    with patch("apps.contas.views.paginas.perfil.render") as render_perfil:
        pagina_perfil(requisicao)

    render_login.assert_called_once_with(requisicao, "contas/autenticacao/login.html")
    render_perfil.assert_called_once_with(requisicao, "contas/perfil.html")
