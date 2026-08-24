"""Renderiza a pagina-shell de um topico de ajuda."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_topico(request: HttpRequest, slug: str) -> HttpResponse:
    """Entrega somente a estrutura e o slug consumido pela API."""
    return render(request, "ajuda/topico.html", {"slug": slug})
