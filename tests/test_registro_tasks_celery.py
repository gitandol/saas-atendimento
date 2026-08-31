"""Garante que o worker inicia com todas as tarefas publicadas registradas."""

import os
import subprocess
import sys


def test_worker_registra_tarefa_de_envio_whatsapp() -> None:
    """Falha se o Celery descartar respostas por nao importar o modulo de envio."""
    ambiente = os.environ.copy()
    ambiente["DJANGO_SETTINGS_MODULE"] = "config.settings.desenvolvimento"
    codigo = (
        "import django; "
        "django.setup(); "
        "from config.celery import app; "
        "app.loader.import_default_modules(); "
        "print('apps.whatsapp.tasks.enviar_mensagem.enviar_mensagem_whatsapp' "
        "in app.tasks)"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "True"
