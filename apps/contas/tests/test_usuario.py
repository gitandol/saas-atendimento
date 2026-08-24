"""Testes do modelo de usuario autenticado por e-mail."""

import pytest
from django.db import IntegrityError

from apps.contas.models import Usuario


@pytest.mark.django_db
def test_usuario_autentica_por_email_e_exige_email_unico():
    """Impede contas duplicadas e usa e-mail normalizado para autenticar."""
    usuario = Usuario.objects.create_user(email="Pessoa@Example.com", password="senha")

    assert usuario.email == "Pessoa@example.com"
    assert usuario.USERNAME_FIELD == "email"

    with pytest.raises(IntegrityError):
        Usuario.objects.create_user(email="Pessoa@example.com")
