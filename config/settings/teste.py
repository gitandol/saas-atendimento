"""Configura testes unitarios isolados de servicos externos."""

from config.settings.base import *  # noqa: F403

SECRET_KEY = "segredo-apenas-para-testes"
IA_CHAVE_CRIPTOGRAFIA = "segredo-ia-apenas-para-testes"
DEBUG = False
STATIC_ROOT = None
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "saas-atendimento-testes",
    }
}
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
