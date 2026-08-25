"""Protege as garantias minimas das configuracoes de producao."""

import os
import subprocess
import sys


def test_producao_recusa_secret_key_vazia() -> None:
    """Impede que a aplicacao de producao inicie sem chave secreta."""
    ambiente = os.environ.copy()
    ambiente.pop("SECRET_KEY", None)
    resultado = subprocess.run(
        [sys.executable, "-c", "import config.settings.producao"],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )
    assert resultado.returncode != 0
    assert "SECRET_KEY" in resultado.stderr


def test_producao_recusa_chave_criptografica_vazia() -> None:
    """Impede iniciar producao sem o segredo dedicado das credenciais de IA."""
    ambiente = os.environ.copy()
    ambiente["SECRET_KEY"] = "segredo-django-de-teste"
    ambiente.pop("IA_CHAVE_CRIPTOGRAFIA", None)
    resultado = subprocess.run(
        [sys.executable, "-c", "import config.settings.producao"],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )
    assert resultado.returncode != 0
    assert "IA_CHAVE_CRIPTOGRAFIA" in resultado.stderr


def test_producao_mantem_debug_desabilitado() -> None:
    """Evita a exposicao de tracebacks mesmo quando DEBUG vem do ambiente."""
    ambiente = os.environ.copy()
    ambiente["SECRET_KEY"] = "segredo-apenas-para-teste"
    ambiente["IA_CHAVE_CRIPTOGRAFIA"] = "segredo-ia-apenas-para-teste"
    ambiente["DEBUG"] = "true"
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            "from config.settings.producao import DEBUG; print(DEBUG)",
        ],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )
    assert resultado.returncode == 0
    assert resultado.stdout.strip() == "False"
