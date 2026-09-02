"""Schemas HTTP de listagem e leitura de conversas."""

from datetime import datetime
from uuid import UUID

from ninja import Schema


class ConversaSaidaSchema(Schema):
    """Publica o resumo operacional exibido na lista."""

    id: UUID
    nome: str
    numero: str
    previa: str
    nao_lidas: int
    nao_respondidas: int
    modo: str
    estado: str
    atendente: str
    versao: int
    atualizado_em: datetime


class ListaConversasSaidaSchema(Schema):
    """Agrupa as conversas visiveis da empresa ativa."""

    conversas: list[ConversaSaidaSchema]


class LeituraConversaSaidaSchema(Schema):
    """Confirma a zeragem do contador de mensagens nao lidas."""

    conversa_id: UUID
    nao_lidas: int


class ErroAtendimentoSchema(Schema):
    """Representa um erro operacional seguro da caixa."""

    codigo: str
    mensagem: str
