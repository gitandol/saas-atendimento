"""Define o contrato HTTP do perfil de usuario."""

from uuid import UUID

from ninja import Schema


class PerfilSaidaSchema(Schema):
    """Expoe usuario, empresa ativa e papel da associacao."""

    email: str
    nome: str
    empresa_id: UUID
    empresa_nome: str
    papel: str
    pode_administrar: bool
