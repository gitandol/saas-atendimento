"""Contratos HTTP de restauracao de revisoes."""

from ninja import Schema


class RestauracaoEntradaSchema(Schema):
    """Recebe o identificador de correlacao exigido pela operacao."""

    correlacao: str
