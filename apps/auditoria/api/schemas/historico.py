"""Contratos HTTP de leitura do historico."""

from datetime import datetime
from uuid import UUID

from ninja import Schema


class ItemHistoricoSchema(Schema):
    """Expoe metadados de um evento sem snapshots internos."""

    id: UUID
    revisao_id: int
    revisao_numero: int
    tipo_objeto: str
    objeto_id: str
    acao: str
    campos_alterados: list[str]
    ator_id: UUID | None
    origem: str
    correlacao: str
    criado_em: datetime


class PaginaHistoricoSchema(Schema):
    """Representa a pagina solicitada e sua contagem total."""

    itens: list[ItemHistoricoSchema]
    pagina: int
    tamanho: int
    total: int


class ErroAuditoriaSchema(Schema):
    """Padroniza falhas esperadas da API de auditoria."""

    codigo: str
    mensagem: str
