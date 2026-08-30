"""Autentica e limita o webhook sem persistir ou expor credenciais."""

import hashlib
import hmac
from uuid import UUID

from django.conf import settings
from django.core.cache import cache

from apps.empresas.models import Empresa
from apps.whatsapp.models import ConfiguracaoWhatsApp

LIMITE_WEBHOOK = 60
JANELA_WEBHOOK_SEGUNDOS = 60


class TokenWebhookInvalido(Exception):
    """Indica que empresa ou assinatura da URL nao sao autenticas."""


class ConfiguracaoWebhookInativa(Exception):
    """Indica que a empresa desativou sua integracao WhatsApp."""


class LimiteWebhookExcedido(Exception):
    """Indica que uma origem excedeu a janela publica do webhook."""


def limitar_webhook(*, empresa_id: UUID, origem: str) -> None:
    """Reserva uma requisicao usando somente um digest opaco no cache."""
    digest = hashlib.sha256(f"{empresa_id}:{origem}".encode()).hexdigest()
    chave = f"webhook:limite:{digest}"
    if cache.add(chave, 1, timeout=JANELA_WEBHOOK_SEGUNDOS):
        return
    try:
        quantidade = cache.incr(chave)
    except ValueError:
        limitar_webhook(empresa_id=empresa_id, origem=origem)
        return
    if quantidade > LIMITE_WEBHOOK:
        raise LimiteWebhookExcedido


def gerar_token_webhook(*, empresa_id: UUID) -> str:
    """Deriva um segredo estavel sem armazenar credenciais em texto claro."""
    mensagem = f"evolution-webhook:{empresa_id}".encode()
    return hmac.new(
        settings.SECRET_KEY.encode(),
        mensagem,
        hashlib.sha256,
    ).hexdigest()


def validar_webhook(*, empresa_id: UUID, token: str) -> Empresa:
    """Retorna a empresa somente quando token e configuracao sao validos."""
    esperado = gerar_token_webhook(empresa_id=empresa_id)
    if len(token) != len(esperado) or not hmac.compare_digest(token, esperado):
        raise TokenWebhookInvalido
    configuracao = (
        ConfiguracaoWhatsApp.objects.select_related("empresa")
        .filter(empresa_id=empresa_id)
        .first()
    )
    if configuracao is None:
        raise TokenWebhookInvalido
    if not configuracao.ativo:
        raise ConfiguracaoWebhookInativa
    return configuracao.empresa
