"""Contratos HTTP das perguntas frequentes."""

from datetime import datetime

from ninja import Schema
from pydantic import Field


class PerguntaFrequenteEntradaSchema(Schema):
    """Valida campos editaveis de uma pergunta frequente."""

    pergunta: str = Field(min_length=1, max_length=500)
    resposta: str = Field(min_length=1, max_length=10000)
    ativo: bool = False
    ordem: int = Field(default=0, ge=0)


class PerguntaFrequenteSaidaSchema(PerguntaFrequenteEntradaSchema):
    """Expoe uma pergunta frequente persistida."""

    id: int
    atualizado_em: datetime


class PaginaPerguntasFrequentesSchema(Schema):
    """Expoe uma pagina de perguntas frequentes."""

    itens: list[PerguntaFrequenteSaidaSchema]
    pagina: int
    tamanho: int
    total: int
