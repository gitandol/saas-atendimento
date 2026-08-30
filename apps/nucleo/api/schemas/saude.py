"""Define os contratos dos endpoints de saude."""

from ninja import Schema


class SaudeSaidaSchema(Schema):
    """Informa se o processo da aplicacao esta operacional."""

    estado: str


class DependenciasSaidaSchema(Schema):
    """Informa o estado agregado e individual das dependencias."""

    estado: str
    componentes: dict[str, str]
