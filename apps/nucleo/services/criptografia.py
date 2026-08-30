"""Cifra valores sensiveis com a chave mestra configurada."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ValorCriptografadoInvalido(Exception):
    """Indica que um valor persistido nao pode ser recuperado."""


def _fernet() -> Fernet:
    """Deriva uma chave Fernet estavel do segredo exclusivo configurado."""
    segredo = settings.IA_CHAVE_CRIPTOGRAFIA
    if not segredo:
        raise ImproperlyConfigured("IA_CHAVE_CRIPTOGRAFIA deve ser configurada.")
    chave = base64.urlsafe_b64encode(hashlib.sha256(segredo.encode()).digest())
    return Fernet(chave)


def criptografar_valor(valor: str) -> str:
    """Retorna o valor cifrado e apropriado para persistencia."""
    return _fernet().encrypt(valor.encode()).decode()


def descriptografar_valor(valor: str) -> str:
    """Recupera um valor cifrado ou informa corrupcao segura."""
    try:
        return _fernet().decrypt(valor.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as erro:
        raise ValorCriptografadoInvalido from erro
