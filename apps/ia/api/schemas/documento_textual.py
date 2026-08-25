"""Contratos HTTP dos documentos textuais."""

from datetime import datetime

from ninja import Schema
from pydantic import Field


class DocumentoTextualEntradaSchema(Schema):
    """Valida campos editaveis de um documento textual."""

    titulo: str = Field(min_length=1, max_length=200)
    conteudo: str = Field(min_length=1, max_length=50000)
    ativo: bool = False
    ordem: int = Field(default=0, ge=0)


class DocumentoTextualSaidaSchema(DocumentoTextualEntradaSchema):
    """Expoe um documento textual persistido."""

    id: int
    atualizado_em: datetime


class PaginaDocumentosSchema(Schema):
    """Expoe uma pagina de documentos textuais."""

    itens: list[DocumentoTextualSaidaSchema]
    pagina: int
    tamanho: int
    total: int
