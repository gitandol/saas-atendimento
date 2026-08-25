"""Renderiza a pagina-shell das perguntas frequentes."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_perguntas_frequentes(request: HttpRequest) -> HttpResponse:
    """Entrega somente a estrutura visual consumida pela API."""
    return render(request, "ia/perguntas_frequentes.html")
