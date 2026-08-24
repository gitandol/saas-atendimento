"""Descreve o erro de validacao nativo do Django Ninja."""

from typing import Any

from ninja import Schema


class ItemErroValidacaoSchema(Schema):
    """Identifica campo, regra e mensagem de uma falha de entrada."""

    type: str
    loc: list[str | int]
    msg: str
    ctx: dict[str, Any] | None = None


class ErroValidacaoSchema(Schema):
    """Agrupa as falhas de validacao do payload HTTP."""

    detail: list[ItemErroValidacaoSchema]
