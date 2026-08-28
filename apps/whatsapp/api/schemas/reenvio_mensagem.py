"""Schemas HTTP do reenvio manual de mensagem."""

from uuid import UUID

from ninja import Schema


class ReenvioMensagemSaidaSchema(Schema):
    """Confirma o agendamento da mesma entidade de mensagem."""

    mensagem_id: UUID
    status: str


class ReenvioMensagemErroSchema(Schema):
    """Publica falhas esperadas sem detalhes internos."""

    codigo: str
    mensagem: str
