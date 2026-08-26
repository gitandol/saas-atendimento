"""Define contratos HTTP da configuracao e conexao do WhatsApp."""

from datetime import datetime

from ninja import Schema
from pydantic import Field

from apps.whatsapp.integrations.protocolos import EstadoConexao


class ConfiguracaoWhatsAppEntradaSchema(Schema):
    """Valida destino, instancia e uma credencial nova opcional."""

    url_base: str = Field(min_length=1, max_length=500)
    nome_instancia: str = Field(min_length=1, max_length=120)
    chave_api: str = Field(default="", max_length=1000)


class ConfiguracaoWhatsAppSaidaSchema(Schema):
    """Expoe configuracao e estado sem incluir a credencial."""

    url_base: str
    nome_instancia: str
    chave_configurada: bool
    ativo: bool
    estado: EstadoConexao
    atualizado_em: datetime | None


class QRCodeWhatsAppSaidaSchema(Schema):
    """Publica o QR Code temporario e sua validade visual."""

    qrcode: str
    expira_em_segundos: int


class ErroWhatsAppSchema(Schema):
    """Padroniza falhas esperadas do modulo WhatsApp."""

    codigo: str
    mensagem: str
