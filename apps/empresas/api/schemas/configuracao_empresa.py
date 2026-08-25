"""Define os contratos HTTP da configuracao da empresa."""

import re
from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from ninja import Schema
from pydantic import Field, field_validator

_VALIDAR_URL_HTTP = URLValidator(schemes=["http", "https"])
_FORMATO_TELEFONE = re.compile(r"^\+?[0-9\s().-]*$")


class EmpresaBaseSchema(Schema):
    """Compartilha os campos publicos do perfil empresarial."""

    nome: str = Field(min_length=1, max_length=160)
    segmento: str = Field(default="", max_length=120)
    descricao: str = Field(default="", max_length=2000)
    horario_atendimento: str = Field(default="", max_length=500)
    endereco: str = Field(default="", max_length=500)
    telefone: str = Field(default="", max_length=30)
    site: str = Field(default="", max_length=500)
    instrucoes_atendimento: str = Field(default="", max_length=4000)


class EmpresaEntradaSchema(EmpresaBaseSchema):
    """Valida a substituicao integral e sua versao de concorrencia."""

    atualizado_em: datetime

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        """Recusa nome composto somente por espacos."""
        valor = valor.strip()
        if not valor:
            raise ValueError("O nome e obrigatorio.")
        return valor

    @field_validator("telefone")
    @classmethod
    def normalizar_telefone(cls, valor: str) -> str:
        """Remove formatacao visual preservando o prefixo internacional."""
        valor = valor.strip()
        if not valor:
            return ""
        if not _FORMATO_TELEFONE.fullmatch(valor):
            raise ValueError("Telefone invalido.")
        prefixo = "+" if valor.startswith("+") else ""
        digitos = "".join(caractere for caractere in valor if caractere.isdigit())
        if not digitos:
            raise ValueError("Telefone invalido.")
        return prefixo + digitos

    @field_validator("site")
    @classmethod
    def validar_site(cls, valor: str) -> str:
        """Aceita site vazio ou URL absoluta HTTP/HTTPS."""
        valor = valor.strip()
        if not valor:
            return ""
        try:
            _VALIDAR_URL_HTTP(valor)
        except DjangoValidationError as erro:
            raise ValueError("Site invalido.") from erro
        return valor


class EmpresaSaidaSchema(EmpresaBaseSchema):
    """Expoe o perfil persistido e a versao usada em novas escritas."""

    atualizado_em: datetime


class ErroEmpresaSchema(Schema):
    """Padroniza falhas esperadas da configuracao empresarial."""

    codigo: str
    mensagem: str
