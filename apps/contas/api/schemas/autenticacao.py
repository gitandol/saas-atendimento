"""Define contratos HTTP de autenticacao."""

from ninja import Schema


class TokenCsrfSaidaSchema(Schema):
    """Expoe o token necessario a requisicoes mutaveis."""

    csrf_token: str


class LoginEntradaSchema(Schema):
    """Recebe credenciais e um destino opcional depois do login."""

    email: str
    senha: str
    proximo: str | None = None


class LoginSaidaSchema(Schema):
    """Informa o destino seguro depois da autenticacao."""

    redirecionar_para: str


class LogoutSaidaSchema(Schema):
    """Confirma que o encerramento de sessao foi solicitado."""

    encerrada: bool
