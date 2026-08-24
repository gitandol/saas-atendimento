"""Testes do servico de encerramento de sessao."""

import pytest
from django.contrib.auth import login
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from apps.contas.models import Usuario
from apps.contas.services.encerrar_sessao import encerrar_sessao


@pytest.mark.django_db
def test_encerrar_sessao_remove_autenticacao_do_usuario():
    """Invalida a autenticacao presente na requisicao."""
    usuario = Usuario.objects.create_user(email="sair@example.com", password="senha")
    requisicao = RequestFactory().post("/")
    requisicao.session = SessionStore()
    login(requisicao, usuario)
    requisicao.user = usuario

    assert encerrar_sessao(requisicao) is None
    assert not requisicao.user.is_authenticated
    assert requisicao.session.get("_auth_user_id") is None
