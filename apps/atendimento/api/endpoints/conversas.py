"""Expoe listagem e leitura de conversas da empresa ativa."""

from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpRequest
from django.shortcuts import render
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.atendimento.api.schemas.conversas import (
    ErroAtendimentoSchema,
    LeituraConversaSaidaSchema,
    ListaConversasSaidaSchema,
)
from apps.atendimento.services.consultas.listar_conversas import listar_conversas
from apps.atendimento.services.conversas import marcar_como_lida
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)

router = Router(tags=["atendimento"], auth=SessionAuth())


def _erro(status: int, codigo: str, mensagem: str) -> Status:
    """Cria uma resposta de erro operacional padronizada."""
    return Status(status, {"codigo": codigo, "mensagem": mensagem})


@router.get(
    "/atendimento/conversas",
    response={200: ListaConversasSaidaSchema, 403: ErroAtendimentoSchema},
)
def consultar_conversas(
    request: HttpRequest,
    busca: str = "",
    filtro: str = "ABERTAS",
):
    """Resolve o tenant e publica os resumos retornados pelo service."""
    try:
        empresa = exigir_empresa_ativa(request)
    except EmpresaAtivaAusente:
        return _erro(403, "permissao_negada", "Acesso negado.")
    conversas = listar_conversas(empresa=empresa, busca=busca, filtro=filtro)
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "atendimento/parciais/lista_conversas.html",
            {"conversas": conversas},
        )
    return {
        "conversas": [
            {
                "id": conversa.id,
                "nome": conversa.contato.nome,
                "numero": conversa.contato.numero_normalizado,
                "previa": conversa.ultima_mensagem_texto,
                "nao_lidas": conversa.contagem_nao_lida,
                "modo": conversa.modo,
                "estado": conversa.estado,
                "atendente": conversa.atendente_nome,
                "atualizado_em": conversa.atualizado_em,
            }
            for conversa in conversas
        ]
    }


@router.post(
    "/atendimento/conversas/{conversa_id}/marcar-lida",
    response={
        200: LeituraConversaSaidaSchema,
        403: ErroAtendimentoSchema,
        404: ErroAtendimentoSchema,
    },
)
def registrar_leitura(request: HttpRequest, conversa_id: UUID):
    """Delega a leitura autorizada sem consultar persistencia na API."""
    try:
        empresa = exigir_empresa_ativa(request)
        conversa = marcar_como_lida(
            empresa=empresa,
            conversa_id=conversa_id,
            ator=request.user,
            correlacao=request.headers.get("X-Correlation-ID") or str(uuid4()),
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _erro(403, "permissao_negada", "Acesso negado.")
    except ObjectDoesNotExist:
        return _erro(404, "conversa_nao_encontrada", "Conversa nao encontrada.")
    return {"conversa_id": conversa.id, "nao_lidas": conversa.contagem_nao_lida}
