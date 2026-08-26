"""Renderiza a pagina-shell da conexao do WhatsApp."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def pagina_configuracao_whatsapp(request: HttpRequest) -> HttpResponse:
    """Entrega somente a estrutura visual consumida pela API."""
    return render(request, "whatsapp/configuracao.html")
