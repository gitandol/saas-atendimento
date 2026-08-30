"""Configura logs JSON com allowlist estrita de metadados operacionais."""

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from apps.nucleo.middleware.correlacao import obter_correlacao

_CAMPOS_OPERACIONAIS = (
    "empresa_id",
    "conversa_id",
    "mensagem_id",
    "tarefa_id",
    "duracao_ms",
    "resultado",
)
_CAMPOS_IDENTIFICADORES = frozenset(_CAMPOS_OPERACIONAIS[:4])
_VALOR_OPERACIONAL = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")

_SEGREDO_WEBHOOK = re.compile(r"(?P<prefix>/api/v1/webhooks/evolution/[^/\s]+/)[^/\s]+")


def _proteger_evento(evento: str) -> str:
    """Remove segredos incorporados em caminhos registrados pelo Django."""
    return _SEGREDO_WEBHOOK.sub(r"\g<prefix>[PROTEGIDO]", evento)


class FormatadorJsonSeguro(logging.Formatter):
    """Serializa somente campos operacionais previamente autorizados."""

    def format(self, record: logging.LogRecord) -> str:
        """Produz uma linha JSON sem payloads, credenciais ou texto livre extra."""
        dados: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "evento": _proteger_evento(record.getMessage()),
            "correlacao": getattr(record, "correlacao", "") or obter_correlacao(),
        }
        for campo in _CAMPOS_OPERACIONAIS:
            valor = getattr(record, campo, None)
            if valor in (None, ""):
                continue
            if campo in _CAMPOS_IDENTIFICADORES and not _VALOR_OPERACIONAL.fullmatch(
                str(valor)
            ):
                continue
            dados[campo] = valor
        if record.exc_info:
            dados["erro_tipo"] = record.exc_info[0].__name__
        return json.dumps(dados, ensure_ascii=False, separators=(",", ":"), default=str)


CONFIGURACAO_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json_seguro": {"()": "config.logging.FormatadorJsonSeguro"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json_seguro",
        },
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
