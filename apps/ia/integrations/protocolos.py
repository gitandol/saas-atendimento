"""Define contratos de dominio independentes do fornecedor de IA."""

from dataclasses import dataclass
from typing import Protocol


class CredencialIAInvalida(Exception):
    """Indica que o fornecedor recusou a credencial configurada."""


class LimiteIAExcedido(Exception):
    """Indica que o limite externo de requisicoes foi atingido."""


class IAIndisponivel(Exception):
    """Indica indisponibilidade ou resposta invalida do fornecedor."""


@dataclass(frozen=True)
class RespostaIA:
    """Representa texto e metricas retornados por um provider de linguagem."""

    texto: str
    modelo: str
    tokens_entrada: int
    tokens_saida: int


class ProviderIA(Protocol):
    """Define a operacao de linguagem usada pelo dominio de atendimento."""

    def gerar_resposta(
        self,
        mensagens: list[dict[str, str]],
        modelo: str,
    ) -> RespostaIA:
        """Gera uma resposta textual para o historico informado."""
        ...
