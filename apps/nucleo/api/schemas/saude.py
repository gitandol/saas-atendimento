"""Define o contrato de saida do endpoint de saude."""

from ninja import Schema


class SaudeSaidaSchema(Schema):
    """Informa se o processo da aplicacao esta operacional."""

    estado: str
