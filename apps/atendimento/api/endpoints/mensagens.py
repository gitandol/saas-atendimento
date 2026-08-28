"""Expoe historico e envio manual da empresa ativa."""

from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import HttpRequest
from django.shortcuts import render
from ninja import Query, Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.atendimento.api.schemas.conversas import ErroAtendimentoSchema
from apps.atendimento.api.schemas.mensagens import (
    EnvioMensagemEntradaSchema,
    HistoricoSaidaSchema,
    MensagemSaidaSchema,
)
from apps.atendimento.services.consultas.obter_historico import obter_historico
from apps.atendimento.services.respostas_manuais import enviar_resposta_manual
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)

router = Router(tags=["atendimento"], auth=SessionAuth())


def _erro(status: int, codigo: str, mensagem: str) -> Status:
    """Cria uma resposta de erro operacional padronizada."""
    return Status(status, {"codigo": codigo, "mensagem": mensagem})


def _serializar_mensagem(mensagem) -> dict[str, object]:
    """Converte o DTO de dominio no contrato publico da API."""
    return {
        "id": mensagem.id,
        "direcao": mensagem.direcao,
        "autor": mensagem.autor,
        "texto": mensagem.texto,
        "status": mensagem.status,
        "erro": mensagem.erro_sanitizado,
        "criado_em": mensagem.criado_em,
        "enviado_em": mensagem.enviado_em,
        "entregue_em": mensagem.entregue_em,
    }


@router.get(
    "/atendimento/conversas/{conversa_id}/mensagens",
    response={
        200: HistoricoSaidaSchema,
        403: ErroAtendimentoSchema,
        404: ErroAtendimentoSchema,
    },
)
def consultar_historico(
    request: HttpRequest,
    conversa_id: UUID,
    cursor: UUID | None = None,
    depois_de: UUID | None = None,
    limite: int = Query(50, ge=1, le=100),
):
    """Publica uma janela do historico sem duplicar o cursor."""
    try:
        empresa = exigir_empresa_ativa(request)
        mensagens = obter_historico(
            empresa=empresa,
            conversa_id=conversa_id,
            cursor=cursor,
            depois_de=depois_de,
            limite=limite + 1,
        )
    except EmpresaAtivaAusente:
        return _erro(403, "permissao_negada", "Acesso negado.")
    except ObjectDoesNotExist:
        return _erro(404, "conversa_nao_encontrada", "Conversa nao encontrada.")
    possui_anterior = depois_de is None and len(mensagens) > limite
    if depois_de is not None and len(mensagens) > limite:
        mensagens = mensagens[:limite]
    elif len(mensagens) > limite:
        mensagens = mensagens[1:]
        possui_anterior = True
    proximo_cursor = mensagens[0].id if possui_anterior and mensagens else None
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "atendimento/parciais/historico_mensagens.html",
            {
                "conversa_id": conversa_id,
                "mensagens": mensagens,
                "proximo_cursor": proximo_cursor,
                "incremental": depois_de is not None,
            },
        )
    return {
        "mensagens": [_serializar_mensagem(mensagem) for mensagem in mensagens],
        "proximo_cursor": proximo_cursor,
    }


@router.post(
    "/atendimento/conversas/{conversa_id}/mensagens",
    response={
        202: MensagemSaidaSchema,
        403: ErroAtendimentoSchema,
        404: ErroAtendimentoSchema,
        409: ErroAtendimentoSchema,
    },
)
def enviar_mensagem(
    request: HttpRequest,
    conversa_id: UUID,
    dados: EnvioMensagemEntradaSchema,
):
    """Converte o payload e delega a resposta manual ao service."""
    try:
        empresa = exigir_empresa_ativa(request)
        mensagem = enviar_resposta_manual(
            empresa=empresa,
            conversa_id=conversa_id,
            texto=dados.texto,
            ator=request.user,
            correlacao=request.headers.get("X-Correlation-ID") or str(uuid4()),
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _erro(403, "permissao_negada", "Acesso negado.")
    except ObjectDoesNotExist:
        return _erro(404, "conversa_nao_encontrada", "Conversa nao encontrada.")
    except ValidationError:
        return _erro(
            409,
            "conversa_finalizada",
            "A conversa nao aceita novas mensagens.",
        )
    return Status(202, _serializar_mensagem(mensagem))
