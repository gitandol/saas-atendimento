"""Renderiza a pagina-shell publica de autenticacao."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def pagina_login(request: HttpRequest) -> HttpResponse:
    """Renderiza o shell de login sem consultar dados de dominio."""
    return render(request, "contas/autenticacao/login.html")
