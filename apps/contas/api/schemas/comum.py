"""Define contratos de erro compartilhados pela API de contas."""

from ninja import Schema


class ErroSaidaSchema(Schema):
    """Representa uma falha de negocio exposta pela API."""

    codigo: str
    mensagem: str


def erro(codigo: str, mensagem: str) -> dict[str, str]:
    """Constroi uma resposta de erro uniforme."""
    return {"codigo": codigo, "mensagem": mensagem}
