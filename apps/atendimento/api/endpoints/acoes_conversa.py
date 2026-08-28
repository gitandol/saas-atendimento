"""Expoe as transicoes explicitas de uma conversa."""

from collections.abc import Callable
from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import HttpRequest
from django.shortcuts import render
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.atendimento.api.schemas.acoes_conversa import (
    AcaoConversaEntradaSchema,
    AcaoConversaSaidaSchema,
    ReabrirConversaEntradaSchema,
)
from apps.atendimento.api.schemas.conversas import ErroAtendimentoSchema
from apps.atendimento.services.assumir_conversa import assumir_conversa
from apps.atendimento.services.devolver_para_ia import devolver_para_ia
from apps.atendimento.services.finalizar_conversa import finalizar_conversa
from apps.atendimento.services.reabrir_conversa import reabrir_conversa
from apps.atendimento.services.transicoes_conversa import ConflitoTransicaoConversa
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)

router = Router(tags=["atendimento"], auth=SessionAuth())


def _erro(status: int, codigo: str, mensagem: str) -> Status:
    """Cria uma resposta operacional segura."""
    return Status(status, {"codigo": codigo, "mensagem": mensagem})


def _serializar(conversa) -> dict[str, object]:
    """Converte o DTO de transicao no contrato HTTP."""
    return {
        "id": conversa.id,
        "modo": conversa.modo,
        "estado": conversa.estado,
        "atendente_id": conversa.atendente_id,
        "atendente": conversa.atendente_nome,
        "versao": conversa.versao,
        "finalizada_em": conversa.finalizada_em,
    }


def _executar(
    *,
    request: HttpRequest,
    conversa_id: UUID,
    dados: AcaoConversaEntradaSchema,
    servico: Callable,
    modo: str | None = None,
):
    """Resolve fronteiras HTTP e delega uma unica transicao ao service."""
    try:
        empresa = exigir_empresa_ativa(request)
        argumentos = {
            "empresa": empresa,
            "conversa_id": conversa_id,
            "ator": request.user,
            "versao": dados.versao,
            "justificativa": dados.justificativa,
            "origem": "api_transferencia",
            "correlacao": request.headers.get("X-Correlation-ID") or str(uuid4()),
        }
        if modo is not None:
            argumentos["modo"] = modo
        conversa = servico(**argumentos)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _erro(403, "permissao_negada", "Acesso negado.")
    except ObjectDoesNotExist:
        return _erro(404, "conversa_nao_encontrada", "Conversa nao encontrada.")
    except ConflitoTransicaoConversa as erro:
        return _erro(409, "conflito_versao", str(erro))
    except ValidationError:
        return _erro(422, "dados_invalidos", "Dados invalidos.")
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "atendimento/parciais/acoes_conversa.html",
            {"conversa": conversa},
        )
    return _serializar(conversa)


RESPOSTAS = {
    200: AcaoConversaSaidaSchema,
    403: ErroAtendimentoSchema,
    404: ErroAtendimentoSchema,
    409: ErroAtendimentoSchema,
    422: ErroAtendimentoSchema,
}


@router.post("/atendimento/conversas/{conversa_id}/assumir", response=RESPOSTAS)
def assumir(request: HttpRequest, conversa_id: UUID, dados: AcaoConversaEntradaSchema):
    """Transfere uma conversa aberta da IA para o ator."""
    return _executar(
        request=request,
        conversa_id=conversa_id,
        dados=dados,
        servico=assumir_conversa,
    )


@router.post(
    "/atendimento/conversas/{conversa_id}/devolver-para-ia",
    response=RESPOSTAS,
)
def devolver(request: HttpRequest, conversa_id: UUID, dados: AcaoConversaEntradaSchema):
    """Devolve a conversa ao modo automatico."""
    return _executar(
        request=request,
        conversa_id=conversa_id,
        dados=dados,
        servico=devolver_para_ia,
    )


@router.post("/atendimento/conversas/{conversa_id}/finalizar", response=RESPOSTAS)
def finalizar(
    request: HttpRequest, conversa_id: UUID, dados: AcaoConversaEntradaSchema
):
    """Finaliza uma conversa aberta."""
    return _executar(
        request=request,
        conversa_id=conversa_id,
        dados=dados,
        servico=finalizar_conversa,
    )


@router.post("/atendimento/conversas/{conversa_id}/reabrir", response=RESPOSTAS)
def reabrir(
    request: HttpRequest, conversa_id: UUID, dados: ReabrirConversaEntradaSchema
):
    """Reabre uma conversa no modo explicitamente selecionado."""
    return _executar(
        request=request,
        conversa_id=conversa_id,
        dados=dados,
        servico=reabrir_conversa,
        modo=dados.modo,
    )
