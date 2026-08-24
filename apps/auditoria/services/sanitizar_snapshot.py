"""Protege valores sensiveis antes da persistencia de snapshots."""

import re
from collections.abc import Mapping, Sequence
from typing import Any

VALOR_PROTEGIDO = "[PROTEGIDO]"
CHAVES_SENSIVEIS = frozenset(
    {
        "senha",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "segredo",
        "secret",
        "client_secret",
        "secret_key",
        "api_key",
        "chave_api",
        "private_key",
    }
)


def _normalizar_chave(chave: object) -> str:
    """Uniformiza caixa, camelCase e separadores antes da classificacao."""
    texto = re.sub(r"(?<!^)(?=[A-Z])", "_", str(chave))
    return re.sub(r"[-\s]+", "_", texto).casefold()


def sanitizar_snapshot(valor: Any) -> Any:
    """Retorna uma copia recursiva com segredos substituidos por marcador."""
    if isinstance(valor, Mapping):
        return {
            chave: (
                VALOR_PROTEGIDO
                if _normalizar_chave(chave) in CHAVES_SENSIVEIS
                else sanitizar_snapshot(conteudo)
            )
            for chave, conteudo in valor.items()
        }
    if isinstance(valor, Sequence) and not isinstance(valor, (str, bytes, bytearray)):
        return [sanitizar_snapshot(item) for item in valor]
    return valor
