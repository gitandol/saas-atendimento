"""Criptografa credenciais de IA antes de sua persistencia."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ChaveCriptografadaInvalida(Exception):
    """Indica que uma credencial persistida nao pode ser recuperada."""


def _fernet() -> Fernet:
    """Deriva uma chave Fernet estavel do segredo exclusivo configurado."""
    segredo = settings.IA_CHAVE_CRIPTOGRAFIA
    if not segredo:
        raise ImproperlyConfigured("IA_CHAVE_CRIPTOGRAFIA deve ser configurada.")
    chave = base64.urlsafe_b64encode(hashlib.sha256(segredo.encode()).digest())
    return Fernet(chave)


def criptografar_chave(chave: str) -> str:
    """Retorna a credencial cifrada e apropriada para persistencia."""
    return _fernet().encrypt(chave.encode()).decode()


def descriptografar_chave(valor: str) -> str:
    """Recupera uma credencial cifrada ou informa corrupcao segura."""
    try:
        return _fernet().decrypt(valor.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as erro:
        raise ChaveCriptografadaInvalida from erro
