"""Renderiza a pagina-shell da configuracao empresarial."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_configuracao_empresa(request: HttpRequest) -> HttpResponse:
    """Entrega somente a estrutura visual consumida pela API."""
    return render(request, "empresas/configuracao.html")
