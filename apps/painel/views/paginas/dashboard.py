"""Renderiza a pagina-shell do dashboard operacional."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_dashboard(request: HttpRequest) -> HttpResponse:
    """Entrega somente a estrutura visual consumida pela API."""
    return render(request, "painel/dashboard.html")
