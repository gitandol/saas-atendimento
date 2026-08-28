"""Schemas HTTP do historico e envio manual."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from ninja import Field, Schema
from pydantic import field_validator


class MensagemSaidaSchema(Schema):
    """Publica conteudo, autoria e entrega de uma mensagem."""

    id: UUID
    direcao: str
    autor: str
    texto: str
    status: str
    erro: str
    criado_em: datetime
    enviado_em: datetime | None
    entregue_em: datetime | None


class HistoricoSaidaSchema(Schema):
    """Agrupa uma pagina cronologica e seu cursor anterior."""

    mensagens: list[MensagemSaidaSchema]
    proximo_cursor: UUID | None


class EnvioMensagemEntradaSchema(Schema):
    """Valida o texto aceito para uma resposta manual."""

    texto: Annotated[str, Field(min_length=1, max_length=4096)]

    @field_validator("texto")
    @classmethod
    def validar_texto_visivel(cls, valor: str) -> str:
        """Recusa conteudo formado somente por espacos."""
        normalizado = valor.strip()
        if not normalizado:
            raise ValueError("O texto e obrigatorio.")
        return normalizado
