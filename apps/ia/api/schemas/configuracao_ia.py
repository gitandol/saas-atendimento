"""Define contratos HTTP da configuracao e do teste de IA."""

from datetime import datetime

from ninja import Schema
from pydantic import Field, field_validator


class ConfiguracaoIAEntradaSchema(Schema):
    """Valida os ajustes editaveis e uma chave nova opcional."""

    modelo: str = Field(min_length=1, max_length=120)
    nome_assistente: str = Field(default="", max_length=120)
    personalidade: str = Field(default="", max_length=4000)
    mensagem_saudacao: str = Field(default="", max_length=1000)
    mensagem_falha: str = Field(default="", max_length=1000)
    respostas_automaticas_ativas: bool = False
    chave_api: str = Field(default="", max_length=500)
    atualizado_em: datetime | None = None

    @field_validator("atualizado_em", mode="before")
    @classmethod
    def normalizar_versao_vazia(cls, valor: object) -> object:
        """Converte o campo oculto vazio em ausencia de versao."""
        return None if valor == "" else valor


class ConfiguracaoIASaidaSchema(Schema):
    """Expoe a configuracao sem incluir a credencial existente."""

    modelo: str
    nome_assistente: str
    personalidade: str
    mensagem_saudacao: str
    mensagem_falha: str
    respostas_automaticas_ativas: bool
    chave_configurada: bool
    atualizado_em: datetime | None


class TesteIAEntradaSchema(Schema):
    """Valida os dados usados exclusivamente no teste de conexao."""

    modelo: str = Field(min_length=1, max_length=120)
    chave_api: str = Field(default="", max_length=500)


class TesteIASaidaSchema(Schema):
    """Informa sucesso sem revelar resposta ou detalhes externos."""

    sucesso: bool
    mensagem: str


class ErroIASchema(Schema):
    """Padroniza falhas esperadas do modulo de IA."""

    codigo: str
    mensagem: str
