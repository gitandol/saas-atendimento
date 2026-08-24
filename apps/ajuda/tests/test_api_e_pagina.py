"""Testes HTTP do topico de ajuda contextual."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_api_de_ajuda_exige_autenticacao_e_retorna_contrato() -> None:
    """Protege o conteudo e publica HTML com data de atualizacao."""
    from apps.contas.models import Usuario

    cliente = Client()
    anonima = cliente.get("/api/v1/ajuda/visao-geral")
    usuario = Usuario.objects.create_user(email="ajuda-api@example.com")
    cliente.force_login(usuario)
    resposta = cliente.get("/api/v1/ajuda/visao-geral")

    assert anonima.status_code == 401
    assert resposta.status_code == 200
    assert set(resposta.json()) == {"slug", "titulo", "html", "atualizado_em"}
    assert resposta.json()["slug"] == "visao-geral"
    assert "<script" not in resposta.json()["html"].casefold()


@pytest.mark.django_db
def test_pagina_de_ajuda_exige_login_e_consume_endpoint() -> None:
    """Renderiza somente o shell autenticado que busca o topico pela API."""
    from apps.contas.models import Usuario

    cliente = Client()
    anonima = cliente.get("/ajuda/visao-geral/")
    usuario = Usuario.objects.create_user(email="ajuda-pagina@example.com")
    cliente.force_login(usuario)
    resposta = cliente.get("/ajuda/visao-geral/")

    assert anonima.status_code == 302
    assert resposta.status_code == 200
    assert b"/api/v1/ajuda/visao-geral" in resposta.content
    assert b"data-atualizado-em" in resposta.content
