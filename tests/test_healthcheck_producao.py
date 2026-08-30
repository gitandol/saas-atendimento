"""Valida o probe web quando HTTPS e obrigatorio."""

import json
import subprocess


def test_healthcheck_web_informa_https_do_proxy() -> None:
    """Evita que o redirect de producao torne o container nao saudavel."""
    resultado = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    servico_web = json.loads(resultado.stdout)["services"]["web"]
    probe = servico_web["healthcheck"]["test"]
    if isinstance(probe, list):
        probe = " ".join(probe)
    assert "X-Forwarded-Proto" in probe
    assert "https" in probe
