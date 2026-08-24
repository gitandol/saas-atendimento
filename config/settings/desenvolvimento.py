"""Configura o ambiente local de desenvolvimento."""

from config.settings.base import *  # noqa: F403

SECRET_KEY = SECRET_KEY or "insegura-apenas-para-desenvolvimento"  # noqa: F405
DEBUG = True
