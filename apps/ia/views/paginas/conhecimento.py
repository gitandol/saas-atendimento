"""Renderiza a pagina-shell dos documentos textuais."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_conhecimento(request: HttpRequest) -> HttpResponse:
    """Entrega somente a estrutura visual consumida pela API."""
    return render(request, "ia/conhecimento.html")
