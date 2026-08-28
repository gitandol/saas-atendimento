"""Schemas HTTP das transicoes de conversa."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from ninja import Field, Schema


class AcaoConversaEntradaSchema(Schema):
    """Recebe a versao otimista e a motivacao operacional opcional."""

    versao: Annotated[int, Field(ge=1)]
    justificativa: Annotated[str, Field(max_length=500)] = ""


class ReabrirConversaEntradaSchema(AcaoConversaEntradaSchema):
    """Define quem conduzira a conversa reaberta."""

    modo: Literal["IA", "HUMANO"] = "IA"


class AcaoConversaSaidaSchema(Schema):
    """Publica o estado necessario para atualizar a caixa."""

    id: UUID
    modo: str
    estado: str
    atendente_id: UUID | None
    atendente: str
    versao: int
    finalizada_em: datetime | None
