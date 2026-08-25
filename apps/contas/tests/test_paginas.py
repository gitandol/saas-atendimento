"""Testes das paginas-shell de contas."""

from unittest.mock import patch

import pytest
from django.test import Client, RequestFactory

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


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
def test_shell_publico_aplica_preferencia_local_do_visitante() -> None:
    """Carrega o tema local no shell publico sem exigir autenticacao."""
    resposta = Client().get("/entrar/")

    conteudo = resposta.content.decode()
    assert 'data-tema="azul"' in conteudo
    assert "preferencia-visual" in conteudo
    assert 'src="/static/src/js/tema.js"' in conteudo


@pytest.mark.django_db
def test_pagina_de_perfil_renderiza_shell_da_api() -> None:
    """Disponibiliza shell cujo conteudo dinamico vem da API versionada."""
    resposta = Client().get("/perfil/")

    assert resposta.status_code == 200
    assert "contas/perfil.html" in [template.name for template in resposta.templates]
    assert b"/api/v1/perfil" in resposta.content


@pytest.mark.django_db
def test_usuario_autenticado_recebe_layout_e_cinco_paletas() -> None:
    """Renderiza landmarks, ajuda e seletor completo no shell autenticado."""
    empresa = Empresa.objects.create(nome="Empresa Layout")
    usuario = Usuario.objects.create_user(email="layout@example.com", password="senha")
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/perfil/")

    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert '<aside id="sidebar"' in conteudo
    assert '<header class="barra-superior"' in conteudo
    assert '<main id="conteudo-principal"' in conteudo
    assert ">Ajuda<" in conteudo
    assert conteudo.count("data-tema-opcao=") == 5
    for tema in ("azul", "esmeralda", "violeta", "rubi", "ambar"):
        assert f'data-tema-opcao="{tema}"' in conteudo
    assert 'aria-expanded="false"' in conteudo


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


@pytest.mark.django_db
def test_pagina_de_login_expoe_composicao_em_duas_colunas() -> None:
    """Entrega hero, acesso e seletor completo no shell publico."""
    resposta = Client().get("/entrar/")
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'class="grade-login"' in conteudo
    assert 'class="apresentacao-login"' in conteudo
    assert 'class="cartao cartao-login"' in conteudo
    assert 'class="formulario-autenticacao"' in conteudo
    assert "Atendimento inteligente" in conteudo
    assert conteudo.count("data-tema-opcao=") == 5
