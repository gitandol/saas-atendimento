"""DTO de leitura de um contato."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContatoDTO:
    """Publica os dados persistidos de um contato sem expor o model."""

    id: UUID
    nome: str
    numero_normalizado: str
    observacoes: str
    primeiro_contato_em: datetime | None
    ultimo_contato_em: datetime | None
