"""Adapta a API HTTP da OpenAI ao protocolo interno de linguagem."""

from typing import Any, Protocol

import requests

from apps.ia.integrations.protocolos import (
    CredencialIAInvalida,
    IAIndisponivel,
    LimiteIAExcedido,
    RespostaIA,
)
from apps.nucleo.middleware.correlacao import obter_correlacao

URL_CHAT_COMPLETIONS = "https://api.openai.com/v1/chat/completions"


class RespostaHTTP(Protocol):
    """Descreve somente a resposta HTTP consumida pelo adaptador."""

    status_code: int

    def json(self) -> object:
        """Decodifica o corpo JSON da resposta."""
        ...


class ClienteHTTP(Protocol):
    """Descreve a operacao HTTP injetavel usada pelo adaptador."""

    def post(self, url: str, **kwargs: object) -> RespostaHTTP:
        """Envia uma requisicao POST para o fornecedor."""
        ...


class ProviderOpenAI:
    """Implementa o protocolo de IA por meio da API HTTP da OpenAI."""

    def __init__(
        self,
        *,
        chave_api: str,
        cliente: ClienteHTTP | None = None,
        timeout: float = 15.0,
    ) -> None:
        """Configura credencial, transporte injetavel e timeout explicito."""
        self._chave_api = chave_api
        self.cliente = cliente or requests.Session()
        self.timeout = timeout

    def gerar_resposta(
        self,
        mensagens: list[dict[str, str]],
        modelo: str,
    ) -> RespostaIA:
        """Solicita uma conclusao e traduz falhas e payloads externos."""
        try:
            resposta = self.cliente.post(
                URL_CHAT_COMPLETIONS,
                headers={
                    "Authorization": f"Bearer {self._chave_api}",
                    "Content-Type": "application/json",
                    "X-Correlation-ID": obter_correlacao(),
                },
                json={"model": modelo, "messages": mensagens},
                timeout=self.timeout,
            )
        except requests.Timeout as erro:
            raise IAIndisponivel("O provedor de IA excedeu o tempo limite.") from erro
        except requests.RequestException as erro:
            raise IAIndisponivel("Nao foi possivel acessar o provedor de IA.") from erro

        if resposta.status_code == 401:
            raise CredencialIAInvalida("A credencial de IA foi recusada.")
        if resposta.status_code == 429:
            raise LimiteIAExcedido("O limite do provedor de IA foi atingido.")
        if resposta.status_code < 200 or resposta.status_code >= 300:
            raise IAIndisponivel("O provedor de IA esta indisponivel.")

        try:
            payload = resposta.json()
            return self._converter_resposta(payload)
        except IAIndisponivel:
            raise
        except (KeyError, TypeError, ValueError, IndexError) as erro:
            raise IAIndisponivel("O provedor retornou uma resposta invalida.") from erro

    @staticmethod
    def _converter_resposta(payload: object) -> RespostaIA:
        """Valida e converte o payload externo no contrato interno."""
        if not isinstance(payload, dict):
            raise IAIndisponivel("O provedor retornou uma resposta invalida.")
        dados: dict[str, Any] = payload
        conteudo = dados["choices"][0]["message"]["content"]
        modelo = dados["model"]
        entrada = dados["usage"]["prompt_tokens"]
        saida = dados["usage"]["completion_tokens"]
        if (
            not isinstance(conteudo, str)
            or not conteudo.strip()
            or not isinstance(modelo, str)
            or not modelo
            or not isinstance(entrada, int)
            or entrada < 0
            or not isinstance(saida, int)
            or saida < 0
        ):
            raise IAIndisponivel("O provedor retornou uma resposta invalida.")
        texto = conteudo.strip()
        return RespostaIA(
            texto=texto,
            modelo=modelo,
            tokens_entrada=entrada,
            tokens_saida=saida,
        )
