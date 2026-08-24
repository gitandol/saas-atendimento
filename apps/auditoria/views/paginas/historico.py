"""Renderiza a pagina-shell do historico."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_historico(request: HttpRequest) -> HttpResponse:
    """Renderiza a estrutura sem consultar modelos ou executar regras."""
    return render(request, "auditoria/historico.html")
