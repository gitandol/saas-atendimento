"""Contrato HTTP de um topico de ajuda."""

from datetime import datetime

from ninja import Schema


class TopicoSaidaSchema(Schema):
    """Publica HTML sanitizado e a data de atualizacao do Markdown."""

    slug: str
    titulo: str
    html: str
    atualizado_em: datetime


class ErroAjudaSchema(Schema):
    """Representa topico de ajuda inexistente."""

    codigo: str
    mensagem: str
