"""Protege valores sensiveis antes da persistencia de snapshots."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder

from apps.nucleo.services.criptografia import criptografar_valor, descriptografar_valor

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
        "telefone",
        "numero_telefone",
        "numero_normalizado",
        "texto",
        "conteudo",
        "prompt",
        "instrucoes_atendimento",
    }
)
MARCADOR_VALOR_CIFRADO = "__valor_cifrado__"
CHAVES_RESTAURAVEIS_PROTEGIDAS = frozenset(
    {
        "telefone",
        "numero_telefone",
        "numero_normalizado",
        "texto",
        "conteudo",
        "prompt",
        "instrucoes_atendimento",
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


def proteger_snapshot_restauravel(valor: Any) -> Any:
    """Cifra conteudo restauravel e mascara credenciais definitivamente."""
    if isinstance(valor, Mapping):
        return {
            chave: (
                {
                    MARCADOR_VALOR_CIFRADO: criptografar_valor(
                        json.dumps(conteudo, cls=DjangoJSONEncoder)
                    )
                }
                if _normalizar_chave(chave) in CHAVES_RESTAURAVEIS_PROTEGIDAS
                else VALOR_PROTEGIDO
                if _normalizar_chave(chave) in CHAVES_SENSIVEIS
                else proteger_snapshot_restauravel(conteudo)
            )
            for chave, conteudo in valor.items()
        }
    if isinstance(valor, Sequence) and not isinstance(valor, (str, bytes, bytearray)):
        return [proteger_snapshot_restauravel(item) for item in valor]
    return valor


def restaurar_snapshot_protegido(valor: Any) -> Any:
    """Decifra somente conteudo restauravel, preservando marcadores de segredo."""
    if isinstance(valor, Mapping):
        if set(valor) == {MARCADOR_VALOR_CIFRADO}:
            cifra = valor[MARCADOR_VALOR_CIFRADO]
            if isinstance(cifra, str):
                return json.loads(descriptografar_valor(cifra))
        return {
            chave: restaurar_snapshot_protegido(conteudo)
            for chave, conteudo in valor.items()
        }
    if isinstance(valor, Sequence) and not isinstance(valor, (str, bytes, bytearray)):
        return [restaurar_snapshot_protegido(item) for item in valor]
    return valor
