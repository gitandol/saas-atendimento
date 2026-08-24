"""Disponibiliza fixtures compartilhadas para os testes do projeto."""

import pytest
from django.test import Client


@pytest.fixture
def cliente() -> Client:
    """Retorna um cliente HTTP que exercita a aplicacao Django real."""
    return Client()
