"""Define os contratos de dominio independentes da Evolution API."""

from enum import StrEnum
from typing import Protocol


class EstadoConexao(StrEnum):
    """Normaliza estados externos exibidos ao operador."""

    DESCONECTADO = "DESCONECTADO"
    AGUARDANDO_QR = "AGUARDANDO_QR"
    CONECTADO = "CONECTADO"
    ERRO = "ERRO"


class CredencialWhatsAppInvalida(Exception):
    """Indica que a Evolution API recusou a credencial configurada."""


class InstanciaWhatsAppNaoEncontrada(Exception):
    """Indica que a instancia solicitada nao existe no fornecedor."""


class LimiteWhatsAppExcedido(Exception):
    """Indica que o limite externo de requisicoes foi atingido."""


class WhatsAppIndisponivel(Exception):
    """Indica indisponibilidade ou resposta invalida do fornecedor."""


class ProviderWhatsApp(Protocol):
    """Isola as operacoes de mensageria requeridas pelo MVP."""

    def obter_qrcode(self) -> str:
        """Obtem o QR Code temporario da instancia."""
        ...

    def consultar_estado(self) -> EstadoConexao:
        """Consulta e normaliza o estado atual da instancia."""
        ...

    def enviar_texto(self, numero: str, texto: str, chave_idempotencia: str) -> str:
        """Envia texto uma unica vez conforme a chave informada."""
        ...

    def conectar(self) -> None:
        """Cria ou inicia a instancia configurada."""
        ...

    def desconectar(self) -> None:
        """Encerra a sessao ativa da instancia."""
        ...
