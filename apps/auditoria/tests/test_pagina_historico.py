"""Testes da pagina-shell do historico."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_historico_autenticado_consume_api_e_exibe_ajuda() -> None:
    """Mantem dados dinamicos na API e oferece ajuda contextual visivel."""
    from apps.contas.models import Usuario

    usuario = Usuario.objects.create_user(email="pagina-historico@example.com")
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/auditoria/historico/")

    assert resposta.status_code == 200
    assert b"/api/v1/auditoria/historico" in resposta.content
    assert b"/ajuda/visao-geral/" in resposta.content
    assert b"Ajuda" in resposta.content
