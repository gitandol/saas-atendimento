"""Expoe o webhook publico e limitado da Evolution API."""

import json
from json import JSONDecodeError
from typing import Any
from uuid import UUID, uuid4

from django.http import HttpRequest, JsonResponse
from ninja import Router

from apps.whatsapp.api.schemas.webhook_evolution import (
    WebhookEvolutionErroSchema,
    WebhookEvolutionRespostaSchema,
)
from apps.whatsapp.services.normalizar_evento import EventoEvolutionInvalido
from apps.whatsapp.services.receber_webhook import (
    EnfileiramentoIndisponivel,
    receber_webhook,
)
from apps.whatsapp.services.validar_webhook import (
    ConfiguracaoWebhookInativa,
    TokenWebhookInvalido,
)

MAXIMO_PAYLOAD_BYTES = 262_144

router = Router(tags=["webhooks"], auth=None)


class TipoConteudoInvalido(Exception):
    """Indica que a requisicao nao declarou JSON."""


class PayloadMuitoGrande(Exception):
    """Indica que o corpo excedeu o limite aceito."""


def _correlacao(request: HttpRequest) -> str:
    """Reaproveita somente uma correlacao curta e segura."""
    valor = request.headers.get("X-Correlation-ID", "")
    return valor if 0 < len(valor) <= 80 else str(uuid4())


def _resposta(
    *,
    dados: dict[str, Any],
    status: int,
    correlacao: str,
) -> JsonResponse:
    """Inclui a correlacao em toda resposta externa."""
    resposta = JsonResponse(dados, status=status)
    resposta["X-Correlation-ID"] = correlacao
    return resposta


def _erro(
    *,
    codigo: str,
    mensagem: str,
    status: int,
    correlacao: str,
) -> JsonResponse:
    """Constroi uma falha publica sem ecoar entrada externa."""
    return _resposta(
        dados={"codigo": codigo, "mensagem": mensagem},
        status=status,
        correlacao=correlacao,
    )


def _ler_payload(request: HttpRequest) -> dict[str, Any]:
    """Valida tipo, tamanho real e JSON antes de chamar o dominio."""
    if request.content_type != "application/json":
        raise TipoConteudoInvalido
    tamanho_declarado = request.headers.get("Content-Length")
    if tamanho_declarado:
        try:
            if int(tamanho_declarado) > MAXIMO_PAYLOAD_BYTES:
                raise PayloadMuitoGrande
        except ValueError as erro:
            raise EventoEvolutionInvalido("Content-Length invalido.") from erro
    corpo = request.body
    if len(corpo) > MAXIMO_PAYLOAD_BYTES:
        raise PayloadMuitoGrande
    try:
        payload = json.loads(corpo)
    except (JSONDecodeError, UnicodeDecodeError) as erro:
        raise EventoEvolutionInvalido("JSON invalido.") from erro
    if not isinstance(payload, dict):
        raise EventoEvolutionInvalido("Payload deve ser um objeto JSON.")
    return payload


@router.post(
    "/webhooks/evolution/{empresa_id}/{token}/",
    response={
        200: WebhookEvolutionRespostaSchema,
        400: WebhookEvolutionErroSchema,
        401: WebhookEvolutionErroSchema,
        409: WebhookEvolutionErroSchema,
        413: WebhookEvolutionErroSchema,
        415: WebhookEvolutionErroSchema,
        503: WebhookEvolutionErroSchema,
    },
)
def webhook_evolution(
    request: HttpRequest,
    empresa_id: UUID,
    token: str,
):
    """Valida a fronteira HTTP e delega todo comportamento ao service."""
    correlacao = _correlacao(request)
    try:
        payload = _ler_payload(request)
        resultado = receber_webhook(
            empresa_id=empresa_id,
            token=token,
            payload=payload,
            correlacao=correlacao,
        )
    except TipoConteudoInvalido:
        return _erro(
            codigo="tipo_nao_suportado",
            mensagem="Envie um objeto JSON.",
            status=415,
            correlacao=correlacao,
        )
    except PayloadMuitoGrande:
        return _erro(
            codigo="payload_muito_grande",
            mensagem="Payload excede o limite permitido.",
            status=413,
            correlacao=correlacao,
        )
    except EventoEvolutionInvalido:
        return _erro(
            codigo="evento_invalido",
            mensagem="Evento Evolution invalido.",
            status=400,
            correlacao=correlacao,
        )
    except TokenWebhookInvalido:
        return _erro(
            codigo="webhook_nao_autorizado",
            mensagem="Webhook nao autorizado.",
            status=401,
            correlacao=correlacao,
        )
    except ConfiguracaoWebhookInativa:
        return _erro(
            codigo="whatsapp_inativo",
            mensagem="Integracao WhatsApp inativa.",
            status=409,
            correlacao=correlacao,
        )
    except EnfileiramentoIndisponivel:
        return _erro(
            codigo="processamento_indisponivel",
            mensagem="Mensagem persistida; repita o envio.",
            status=503,
            correlacao=correlacao,
        )

    if resultado.mensagem_id is None:
        status_recebimento = "ignorado"
    elif resultado.criado:
        status_recebimento = "recebido"
    else:
        status_recebimento = "duplicado"
    return _resposta(
        dados={
            "status": status_recebimento,
            "mensagem_id": resultado.mensagem_id,
        },
        status=200,
        correlacao=correlacao,
    )
