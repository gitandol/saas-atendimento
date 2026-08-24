"""Renderiza a pagina-shell de perfil."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def pagina_perfil(request: HttpRequest) -> HttpResponse:
    """Renderiza o shell de perfil sem consultar dados de dominio."""
    return render(request, "contas/perfil.html")
