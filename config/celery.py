"""Configura o worker Celery a partir dos settings Django."""

import os

from celery import Celery
from celery.signals import before_task_publish, task_postrun, task_prerun

from apps.nucleo.middleware.correlacao import (
    definir_correlacao,
    obter_correlacao,
    restaurar_correlacao,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.producao")

app = Celery("atendimento")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@before_task_publish.connect
def propagar_correlacao(headers=None, **_kwargs) -> None:
    """Inclui a correlacao atual nos headers da mensagem Celery."""
    if headers is not None:
        headers["correlacao"] = obter_correlacao()


@task_prerun.connect
def ativar_correlacao_tarefa(task=None, **_kwargs) -> None:
    """Ativa no worker a correlacao recebida pelo broker."""
    if task is None:
        return
    headers = getattr(task.request, "headers", None) or {}
    token = definir_correlacao(headers.get("correlacao"))
    task.request._token_correlacao = token


@task_postrun.connect
def finalizar_correlacao_tarefa(task=None, **_kwargs) -> None:
    """Restaura o contexto do worker depois da execucao da tarefa."""
    if task is None:
        return
    token = getattr(task.request, "_token_correlacao", None)
    if token is not None:
        restaurar_correlacao(token)
        del task.request._token_correlacao
