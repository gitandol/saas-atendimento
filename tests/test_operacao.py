"""Valida que o bootstrap declarado pode iniciar o MVP do zero."""

import json
import subprocess
from pathlib import Path


def _compose() -> dict:
    """Renderiza a configuracao efetiva pelo proprio Docker Compose."""
    resultado = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return json.loads(resultado.stdout)


def test_compose_prepara_aplicacao_e_separa_healthchecks() -> None:
    """Exige migrations, estaticos e healthchecks por componente."""
    servicos = _compose()["services"]

    for nome in ("web", "worker", "postgres", "redis"):
        assert servicos[nome]["healthcheck"]["test"], nome
    comando_web = servicos["web"]["command"]
    if isinstance(comando_web, list):
        comando_web = " ".join(comando_web)
    assert "manage.py migrate --noinput" in comando_web
    assert "manage.py collectstatic --noinput" in comando_web
    assert "gunicorn" in comando_web


def test_compose_propaga_segredos_e_configuracao_a_web_e_worker() -> None:
    """Mantem os dois processos no mesmo ambiente sem defaults produtivos."""
    servicos = _compose()["services"]

    for nome in ("web", "worker"):
        ambiente = servicos[nome]["environment"]
        assert ambiente["DJANGO_SETTINGS_MODULE"]
        assert ambiente["SECRET_KEY"]
        assert ambiente["IA_CHAVE_CRIPTOGRAFIA"]
        assert ambiente["REDIS_URL"]
        assert ambiente["POSTGRES_HOST"] == "postgres"


def test_env_example_documenta_variaveis_operacionais() -> None:
    """Mantem o contrato de ambiente completo e sem valores vazios."""
    variaveis = {
        chave: valor
        for linha in Path(".env.example").read_text(encoding="utf-8").splitlines()
        if linha and not linha.startswith("#") and "=" in linha
        for chave, valor in [linha.split("=", 1)]
    }

    esperadas = {
        "DJANGO_SETTINGS_MODULE",
        "SECRET_KEY",
        "IA_CHAVE_CRIPTOGRAFIA",
        "ALLOWED_HOSTS",
        "CSRF_TRUSTED_ORIGINS",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "REDIS_URL",
        "EVOLUTION_API_KEY",
        "EVOLUTION_POSTGRES_DB",
        "EVOLUTION_POSTGRES_USER",
        "EVOLUTION_POSTGRES_PASSWORD",
        "EVOLUTION_INTERNAL_URL",
        "WHATSAPP_HOSTS_INTERNOS_PERMITIDOS",
        "LOG_LEVEL",
    }
    assert variaveis.keys() >= esperadas
    assert all(variaveis[chave] for chave in esperadas)
