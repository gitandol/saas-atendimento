"""DTO de leitura de uma mensagem."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MensagemDTO:
    """Publica conteudo e estado de entrega sem expor o model."""

    id: UUID
    conversa_id: UUID
    direcao: str
    autor: str
    texto: str
    identificador_externo: str
    status: str
    erro_sanitizado: str
    enviado_em: datetime | None
    entregue_em: datetime | None
    criado_em: datetime
