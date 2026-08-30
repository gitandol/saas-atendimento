"""Valida as protecoes HTTP e os limites das fronteiras publicas."""

import json
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import override_settings


def test_settings_de_producao_endurecem_transporte_e_cookies() -> None:
    """Exige HTTPS, HSTS e cookies seguros com politica explicita."""
    ambiente = os.environ.copy()
    ambiente["SECRET_KEY"] = "segredo-django-de-teste"
    ambiente["IA_CHAVE_CRIPTOGRAFIA"] = "segredo-ia-de-teste"
    codigo = (
        "import json; import config.settings.producao as s; "
        "print(json.dumps({"
        "'ssl': s.SECURE_SSL_REDIRECT,"
        "'hsts': s.SECURE_HSTS_SECONDS,"
        "'subdominios': s.SECURE_HSTS_INCLUDE_SUBDOMAINS,"
        "'preload': s.SECURE_HSTS_PRELOAD,"
        "'sessao_http_only': s.SESSION_COOKIE_HTTPONLY,"
        "'sessao_same_site': s.SESSION_COOKIE_SAMESITE,"
        "'csrf_http_only': s.CSRF_COOKIE_HTTPONLY,"
        "'csrf_same_site': s.CSRF_COOKIE_SAMESITE,"
        "'limite': s.DATA_UPLOAD_MAX_MEMORY_SIZE"
        "}))"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout) == {
        "ssl": True,
        "hsts": 31_536_000,
        "subdominios": True,
        "preload": True,
        "sessao_http_only": True,
        "sessao_same_site": "Lax",
        "csrf_http_only": True,
        "csrf_same_site": "Lax",
        "limite": 262_144,
    }


@override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=16)
def test_webhook_converte_limite_global_de_corpo_em_413(cliente) -> None:
    """Recusa o corpo antes de autenticar ou materializar payload excessivo."""
    resposta = cliente.post(
        f"/api/v1/webhooks/evolution/{uuid4()}/token-invalido/",
        data=b'{"texto":"conteudo-que-excede-o-limite"}',
        content_type="application/json",
    )

    assert resposta.status_code == 413
    assert resposta.json()["codigo"] == "payload_muito_grande"


@pytest.mark.django_db
def test_webhook_limita_requisicoes_por_empresa_e_origem() -> None:
    """Bloqueia rajadas sem guardar IP ou UUID em texto claro no cache."""
    from apps.whatsapp.services.validar_webhook import (
        LimiteWebhookExcedido,
        limitar_webhook,
    )

    cache.clear()
    empresa_id = uuid4()
    for _ in range(60):
        limitar_webhook(empresa_id=empresa_id, origem="192.0.2.10")

    with pytest.raises(LimiteWebhookExcedido):
        limitar_webhook(empresa_id=empresa_id, origem="192.0.2.10")


def test_settings_leem_origens_csrf_e_nivel_de_log_do_ambiente() -> None:
    """Permite configurar a fronteira TLS e a verbosidade sem editar codigo."""
    ambiente = os.environ.copy()
    ambiente["SECRET_KEY"] = "segredo-django-de-teste"
    ambiente["IA_CHAVE_CRIPTOGRAFIA"] = "segredo-ia-de-teste"
    ambiente["CSRF_TRUSTED_ORIGINS"] = (
        "https://app.example.com, https://admin.example.com"
    )
    ambiente["LOG_LEVEL"] = "ERROR"
    codigo = (
        "import json; import config.settings.producao as s; "
        "print(json.dumps({"
        "'origens': s.CSRF_TRUSTED_ORIGINS,"
        "'nivel': s.LOGGING['root']['level']"
        "}))"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout) == {
        "origens": ["https://app.example.com", "https://admin.example.com"],
        "nivel": "ERROR",
    }
