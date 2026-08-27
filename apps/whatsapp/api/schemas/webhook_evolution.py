"""Define respostas publicas do webhook externo da Evolution."""

from uuid import UUID

from ninja import Schema


class WebhookEvolutionRespostaSchema(Schema):
    """Confirma recebimento sem devolver dados da mensagem."""

    status: str
    mensagem_id: UUID | None = None


class WebhookEvolutionErroSchema(Schema):
    """Publica falhas esperadas sem detalhes internos ou segredos."""

    codigo: str
    mensagem: str
