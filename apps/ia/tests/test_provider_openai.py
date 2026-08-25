"""Testes do provider OpenAI isolado por uma fronteira HTTP falsa."""

from dataclasses import dataclass

import pytest
import requests


@dataclass
class RespostaHTTPFalsa:
    """Representa a parte da resposta HTTP consumida pelo provider."""

    status_code: int
    payload: object

    def json(self) -> object:
        """Entrega o payload configurado pelo caso de teste."""
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class ClienteHTTPFalso:
    """Registra a chamada e devolve uma resposta ou excecao controlada."""

    def __init__(self, resultado: object) -> None:
        """Guarda o resultado que sera produzido pela unica chamada."""
        self.resultado = resultado
        self.chamada: dict[str, object] | None = None

    def post(self, url: str, **kwargs: object) -> RespostaHTTPFalsa:
        """Simula a operacao externa sem acessar a rede."""
        self.chamada = {"url": url, **kwargs}
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado  # type: ignore[return-value]


def _provider(resultado: object):
    """Cria o provider real com a fronteira HTTP controlada."""
    from apps.ia.integrations.openai import ProviderOpenAI

    return ProviderOpenAI(
        chave_api="sk-teste",
        cliente=ClienteHTTPFalso(resultado),
        timeout=7.5,
    )


def test_provider_normaliza_resposta_e_metricas() -> None:
    """Converte a resposta externa completa no contrato de dominio."""
    resposta_http = RespostaHTTPFalsa(
        200,
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1787666400,
            "model": "gpt-4.1-mini-2025-04-14",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Ola!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            },
        },
    )
    provider = _provider(resposta_http)

    resposta = provider.gerar_resposta(
        [{"role": "user", "content": "Oi"}],
        "gpt-4.1-mini",
    )

    assert resposta.texto == "Ola!"
    assert resposta.modelo == "gpt-4.1-mini-2025-04-14"
    assert resposta.tokens_entrada == 12
    assert resposta.tokens_saida == 3
    chamada = provider.cliente.chamada
    assert chamada is not None
    assert chamada["timeout"] == 7.5
    assert chamada["json"] == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "Oi"}],
    }


@pytest.mark.parametrize(
    ("resultado", "excecao"),
    [
        (requests.Timeout("tempo excedido"), "IAIndisponivel"),
        (
            RespostaHTTPFalsa(401, {"error": {"message": "invalid key"}}),
            "CredencialIAInvalida",
        ),
        (
            RespostaHTTPFalsa(429, {"error": {"message": "rate limit"}}),
            "LimiteIAExcedido",
        ),
        (RespostaHTTPFalsa(503, {"error": {"message": "down"}}), "IAIndisponivel"),
    ],
)
def test_provider_traduz_falhas_externas(resultado: object, excecao: str) -> None:
    """Converte transporte e status externos em excecoes estaveis do dominio."""
    from apps.ia.integrations.protocolos import (
        CredencialIAInvalida,
        IAIndisponivel,
        LimiteIAExcedido,
    )

    tipos = {
        "CredencialIAInvalida": CredencialIAInvalida,
        "LimiteIAExcedido": LimiteIAExcedido,
        "IAIndisponivel": IAIndisponivel,
    }

    with pytest.raises(tipos[excecao]):
        _provider(resultado).gerar_resposta([], "gpt-4.1-mini")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "model": "gpt-4.1-mini",
            "choices": [{"message": {"content": ""}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 0},
        },
        {"model": "gpt-4.1-mini", "choices": [], "usage": {}},
        ValueError("json invalido"),
    ],
)
def test_provider_recusa_resposta_vazia_ou_invalida(payload: object) -> None:
    """Nao permite que payload incompleto atravesse a fronteira externa."""
    from apps.ia.integrations.protocolos import IAIndisponivel

    with pytest.raises(IAIndisponivel):
        _provider(RespostaHTTPFalsa(200, payload)).gerar_resposta([], "gpt-4.1-mini")


@pytest.mark.parametrize("conteudo", [None, 42, ["texto"]])
def test_provider_traduz_conteudo_nao_textual_em_indisponibilidade(
    conteudo: object,
) -> None:
    """Impede que tipos inesperados escapem como erro interno."""
    from apps.ia.integrations.protocolos import IAIndisponivel

    payload = {
        "model": "gpt-4.1-mini",
        "choices": [{"message": {"content": conteudo}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    with pytest.raises(IAIndisponivel):
        _provider(RespostaHTTPFalsa(200, payload)).gerar_resposta([], "gpt-4.1-mini")
