"""Mantem um identificador seguro entre a requisicao e seus efeitos."""

import re
from contextvars import ContextVar, Token
from uuid import uuid4

from django.http import HttpRequest, HttpResponse

_PADRAO_CORRELACAO = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
_correlacao_atual: ContextVar[str] = ContextVar("correlacao_atual", default="")


def normalizar_correlacao(valor: str | None) -> str:
    """Aceita somente identificadores curtos ou gera um UUID novo."""
    if valor and _PADRAO_CORRELACAO.fullmatch(valor):
        return valor
    return str(uuid4())


def definir_correlacao(valor: str | None) -> Token[str]:
    """Define a correlacao segura no contexto atual e retorna seu token."""
    return _correlacao_atual.set(normalizar_correlacao(valor))


def obter_correlacao() -> str:
    """Retorna a correlacao atual, criando uma quando o contexto esta vazio."""
    valor = _correlacao_atual.get()
    if valor:
        return valor
    valor = normalizar_correlacao(None)
    _correlacao_atual.set(valor)
    return valor


def restaurar_correlacao(token: Token[str]) -> None:
    """Restaura o contexto anterior ao terminar uma fronteira."""
    _correlacao_atual.reset(token)


class CorrelacaoMiddleware:
    """Propaga uma correlacao segura entre cabecalhos e contexto interno."""

    def __init__(self, get_response) -> None:
        """Recebe o proximo componente da cadeia Django."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Ativa a correlacao durante a requisicao e a devolve na resposta."""
        token = definir_correlacao(request.headers.get("X-Correlation-ID"))
        correlacao = obter_correlacao()
        request.correlacao = correlacao
        request.META["HTTP_X_CORRELATION_ID"] = correlacao
        request.__dict__.pop("headers", None)
        try:
            resposta = self.get_response(request)
            resposta["X-Correlation-ID"] = correlacao
            return resposta
        finally:
            restaurar_correlacao(token)
