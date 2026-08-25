"""Configura o ambiente local de desenvolvimento."""

from config.settings.base import *  # noqa: F403

SECRET_KEY = SECRET_KEY or "insegura-apenas-para-desenvolvimento"  # noqa: F405
IA_CHAVE_CRIPTOGRAFIA = (  # noqa: F405
    IA_CHAVE_CRIPTOGRAFIA or "insegura-ia-apenas-para-desenvolvimento"
)
DEBUG = True
