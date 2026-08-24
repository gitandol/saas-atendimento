"""Encerra a sessao autenticada da requisicao."""

from django.contrib.auth import logout


def encerrar_sessao(request) -> None:
    """Invalida a sessao e remove o usuario autenticado da requisicao."""
    logout(request)
