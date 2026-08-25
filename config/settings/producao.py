"""Configura producao com defaults seguros e validacao de segredos."""

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY e obrigatoria em producao")
if not IA_CHAVE_CRIPTOGRAFIA:  # noqa: F405
    raise ImproperlyConfigured("IA_CHAVE_CRIPTOGRAFIA e obrigatoria em producao")

DEBUG = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
