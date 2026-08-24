"""Monta a API versionada e padroniza erros inesperados."""

from typing import Any
from uuid import uuid4

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI, Schema

from apps.contas.api.router import router as contas_router
from apps.nucleo.api.router import router as nucleo_router


class ErroSchema(Schema):
    """Representa o contrato HTTP comum para respostas de erro."""

    codigo: str
    mensagem: str
    detalhes: dict[str, Any] | None
    correlacao: str


api = NinjaAPI(
    title="Atendimento API",
    version="1.0.0",
    docs_url="/docs",
    docs_decorator=staff_member_required if settings.DOCS_AUTENTICADA else None,
)
api.add_router("", contas_router)
api.add_router("", nucleo_router)


@api.exception_handler(Exception)
def tratar_erro_inesperado(request: HttpRequest, _exc: Exception) -> HttpResponse:
    """Oculta detalhes internos e devolve um identificador de correlacao."""
    correlacao = request.headers.get("X-Correlation-ID") or str(uuid4())
    resposta = api.create_response(
        request,
        {
            "codigo": "erro_interno",
            "mensagem": "Nao foi possivel processar a solicitacao.",
            "detalhes": None,
            "correlacao": correlacao,
        },
        status=500,
    )
    resposta["X-Correlation-ID"] = correlacao
    return resposta
