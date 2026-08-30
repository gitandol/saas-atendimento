"""Protege a correlacao e a sanitizacao dos logs operacionais."""

import json
import logging
from uuid import UUID

from django.http import HttpRequest, HttpResponse

from apps.nucleo.middleware.correlacao import CorrelacaoMiddleware
from config.logging import FormatadorJsonSeguro


def test_middleware_reutiliza_correlacao_segura(cliente) -> None:
    """Devolve a mesma correlacao curta recebida pela fronteira HTTP."""
    resposta = cliente.get(
        "/api/v1/saude",
        headers={"X-Correlation-ID": "aceite-016"},
    )

    assert resposta["X-Correlation-ID"] == "aceite-016"


def test_middleware_substitui_correlacao_invalida(cliente) -> None:
    """Impede que valores longos controlados pelo cliente contaminem logs."""
    resposta = cliente.get(
        "/api/v1/saude",
        headers={"X-Correlation-ID": "x" * 81},
    )

    assert resposta["X-Correlation-ID"] != "x" * 81
    UUID(resposta["X-Correlation-ID"])


def test_middleware_substitui_correlacao_antes_da_aplicacao() -> None:
    """Entrega apenas a correlacao normalizada para as camadas internas."""
    correlacao_recebida = ""

    def aplicacao(request: HttpRequest) -> HttpResponse:
        nonlocal correlacao_recebida
        correlacao_recebida = request.headers["X-Correlation-ID"]
        return HttpResponse()

    request = HttpRequest()
    request.META["HTTP_X_CORRELATION_ID"] = "valor com espacos"

    resposta = CorrelacaoMiddleware(aplicacao)(request)

    assert correlacao_recebida == resposta["X-Correlation-ID"]
    UUID(correlacao_recebida)


def test_formatador_json_omite_dados_sensiveis() -> None:
    """Mantem somente metadados operacionais na saida estruturada."""
    registro = logging.LogRecord(
        "teste",
        logging.INFO,
        __file__,
        1,
        "mensagem_processada",
        (),
        None,
    )
    registro.correlacao = "corr-1"
    registro.empresa_id = "empresa-1"
    registro.texto = "conteudo privado"
    registro.numero_telefone = "telefone privado"
    registro.prompt = "prompt privado"
    registro.chave_api = "segredo privado"

    dados = json.loads(FormatadorJsonSeguro().format(registro))

    assert dados["evento"] == "mensagem_processada"
    assert dados["correlacao"] == "corr-1"
    assert dados["empresa_id"] == "empresa-1"
    assert "conteudo privado" not in dados.values()
    assert "telefone privado" not in dados.values()
    assert "prompt privado" not in dados.values()
    assert "segredo privado" not in dados.values()


def test_formatador_json_protege_token_de_webhook_no_evento() -> None:
    """Nao expoe o segredo presente no caminho de um webhook rejeitado."""
    segredo = "token-super-secreto"
    registro = logging.LogRecord(
        "django.request",
        logging.WARNING,
        __file__,
        1,
        f"Not Found: /api/v1/webhooks/evolution/empresa-1/{segredo}/",
        (),
        None,
    )

    saida = FormatadorJsonSeguro().format(registro)

    assert segredo not in saida
    assert "[PROTEGIDO]" in saida


def test_celery_propaga_correlacao_em_headers() -> None:
    """Transporta a correlacao HTTP para o contexto da tarefa Celery."""
    from types import SimpleNamespace

    from apps.nucleo.middleware.correlacao import (
        definir_correlacao,
        obter_correlacao,
        restaurar_correlacao,
    )
    from config.celery import (
        ativar_correlacao_tarefa,
        finalizar_correlacao_tarefa,
        propagar_correlacao,
    )

    headers: dict[str, str] = {}
    token = definir_correlacao("corr-celery")
    try:
        propagar_correlacao(headers=headers)
    finally:
        restaurar_correlacao(token)

    tarefa = SimpleNamespace(request=SimpleNamespace(headers=headers))
    ativar_correlacao_tarefa(task=tarefa)
    try:
        assert obter_correlacao() == "corr-celery"
    finally:
        finalizar_correlacao_tarefa(task=tarefa)
