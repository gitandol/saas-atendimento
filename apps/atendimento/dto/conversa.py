"""DTO de leitura de uma conversa."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.atendimento.dto.contato import ContatoDTO


@dataclass(frozen=True, slots=True)
class ConversaDTO:
    """Publica o estado operacional da conversa e seu contato."""

    id: UUID
    contato: ContatoDTO
    modo: str
    estado: str
    atendente_id: UUID | None
    ultima_mensagem_id: UUID | None
    contagem_nao_lida: int
    finalizada_em: datetime | None
    criado_em: datetime
    atualizado_em: datetime
    ultima_mensagem_texto: str = ""
    atendente_nome: str = ""
