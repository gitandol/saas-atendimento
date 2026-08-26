"""Testes das paginas-shell de conhecimento textual e FAQ."""

import pytest
from django.test import Client

from apps.contas.models import Usuario


def _cliente_autenticado(email: str) -> Client:
    """Cria uma sessao autenticada para testar paginas-base."""
    cliente = Client()
    cliente.force_login(Usuario.objects.create_user(email=email))
    return cliente


@pytest.mark.django_db
@pytest.mark.parametrize("rota", ["/ia/conhecimentos/", "/ia/perguntas-frequentes/"])
def test_paginas_de_conhecimento_exigem_autenticacao(rota: str) -> None:
    """Protege ambas as paginas por sessao Django."""
    assert Client().get(rota).status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rota", "href_ativo"),
    [
        ("/ia/configuracao/", "/ia/configuracao/"),
        ("/ia/conhecimentos/", "/ia/conhecimentos/"),
        ("/ia/perguntas-frequentes/", "/ia/perguntas-frequentes/"),
    ],
)
def test_submenu_ia_abre_e_seleciona_apenas_a_rota_atual(
    rota: str, href_ativo: str
) -> None:
    """Destaca somente a opcao filha correspondente dentro do menu IA."""
    identificador = href_ativo.strip("/").replace("/", "-")
    resposta = _cliente_autenticado(f"menu-{identificador}@example.com").get(rota)
    html = resposta.content.decode()

    assert '<details class="grupo-navegacao-ia" open>' in html
    assert (
        f'class="item-navegacao item-navegacao-ativo" href="{href_ativo}" '
        'aria-current="page"' in html
    )
    assert html.count('aria-current="page"') == 1


@pytest.mark.django_db
def test_pagina_documentos_consume_api_e_exibe_estados_e_ajuda() -> None:
    """Entrega shell HTMX com feedback acessivel e ajuda contextual."""
    resposta = _cliente_autenticado("pagina-doc@example.com").get("/ia/conhecimentos/")
    assert resposta.status_code == 200
    assert b'hx-get="/api/v1/ia/conhecimentos"' in resposta.content
    assert b'hx-delete="/api/v1/ia/conhecimentos/__id__"' in resposta.content
    assert b"Carregando conhecimentos" in resposta.content
    assert b"Nenhum conhecimento cadastrado" in resposta.content
    assert b"Nao foi possivel carregar" in resposta.content
    assert b"/ajuda/base-de-conhecimento/" in resposta.content


@pytest.mark.django_db
def test_pagina_documentos_usa_modal_e_tabela_somente_quando_ha_dados() -> None:
    """Mantem o cadastro no modal e separa tabela do estado vazio."""
    resposta = _cliente_autenticado("layout-doc@example.com").get("/ia/conhecimentos/")

    assert resposta.status_code == 200
    assert b'id="abrir-modal-conhecimento"' in resposta.content
    assert b'class="botao-novo-conhecimento"' in resposta.content
    assert (
        b'<dialog id="modal-conhecimento" class="modal-centralizado"'
        in resposta.content
    )
    assert b'id="formulario-conhecimento"' in resposta.content
    assert b'<table id="tabela-conhecimentos"' in resposta.content
    assert b'<tbody id="corpo-tabela-conhecimentos">' in resposta.content
    assert b'id="estado-vazio-conhecimentos"' in resposta.content
    assert b"dados.total === 0" in resposta.content


@pytest.mark.django_db
def test_pagina_faq_usa_modal_centralizado_e_tabela_somente_com_dados() -> None:
    """Mantem cadastro e edicao no modal e separa tabela do estado vazio."""
    resposta = _cliente_autenticado("layout-faq@example.com").get(
        "/ia/perguntas-frequentes/"
    )

    assert resposta.status_code == 200
    assert b'id="abrir-modal-faq"' in resposta.content
    assert b'class="botao-novo-conhecimento"' in resposta.content
    assert b'<dialog id="modal-faq" class="modal-centralizado"' in resposta.content
    assert b'id="formulario-faq"' in resposta.content
    assert b'<table id="tabela-faq"' in resposta.content
    assert b'<tbody id="corpo-tabela-faq">' in resposta.content
    assert b'id="estado-vazio-faq"' in resposta.content
    assert (
        b'id="regiao-tabela-faq" class="tabela-responsiva" hidden' in resposta.content
    )
    assert b"const semDados = dados.total === 0" in resposta.content


@pytest.mark.django_db
def test_pagina_faq_consume_api_e_sidebar_exibe_acessos() -> None:
    """Entrega a shell de FAQ e mantem as duas telas navegaveis."""
    cliente = _cliente_autenticado("pagina-faq@example.com")
    resposta = cliente.get("/ia/perguntas-frequentes/")
    sidebar = cliente.get("/perfil/")
    assert resposta.status_code == 200
    assert b'hx-get="/api/v1/ia/perguntas-frequentes"' in resposta.content
    assert b'"/api/v1/ia/perguntas-frequentes"' in resposta.content
    assert b"/api/v1/ia/perguntas-frequentes/" in resposta.content
    assert b'hx-delete="/api/v1/ia/perguntas-frequentes/__id__"' in resposta.content
    assert b"/ajuda/base-de-conhecimento/" in resposta.content
    assert b'href="/ia/conhecimentos/"' in sidebar.content
    assert b'href="/ia/perguntas-frequentes/"' in sidebar.content


@pytest.mark.django_db
def test_ajuda_explica_conteudo_seguro_e_limites_do_mvp() -> None:
    """Documenta exemplos seguros e ausencia de PDFs, URLs e RAG."""
    resposta = _cliente_autenticado("ajuda-conhecimento@example.com").get(
        "/api/v1/ajuda/base-de-conhecimento"
    )
    assert resposta.status_code == 200
    html = resposta.json()["html"]
    assert "PDFs" in html
    assert "URLs" in html
    assert "RAG" in html
    assert "Ignore instrucoes" in html
