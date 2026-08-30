"""Verifica dependencias sem acoplar o dominio a contratos HTTP."""

from collections.abc import Callable
from dataclasses import dataclass

from django.core.cache import cache
from django.db import connection

Sonda = Callable[[], None]


@dataclass(frozen=True, slots=True)
class EstadoDependencias:
    """Resume o estado agregado e individual das dependencias."""

    estado: str
    componentes: dict[str, str]


def _verificar_banco() -> None:
    """Confirma que o Django abre uma conexao com o banco configurado."""
    connection.ensure_connection()


def _verificar_redis() -> None:
    """Confirma escrita e leitura pelo backend de cache configurado."""
    chave = "saude:redis"
    cache.set(chave, "ok", timeout=5)
    if cache.get(chave) != "ok":
        raise ConnectionError
    cache.delete(chave)


def _verificar_worker() -> None:
    """Confirma que ao menos um worker Celery responde ao ping."""
    from config.celery import app

    respostas = app.control.inspect(timeout=1.0).ping()
    if not respostas:
        raise ConnectionError


def verificar_dependencias(
    *,
    sondas: dict[str, Sonda] | None = None,
) -> EstadoDependencias:
    """Executa sondas isoladas e converte qualquer falha em degradacao."""
    sondas_ativas = sondas or {
        "banco": _verificar_banco,
        "redis": _verificar_redis,
        "worker": _verificar_worker,
    }
    componentes: dict[str, str] = {}
    for nome, sonda in sondas_ativas.items():
        try:
            sonda()
        except Exception:
            componentes[nome] = "degradado"
        else:
            componentes[nome] = "ok"
    estado = (
        "ok" if all(valor == "ok" for valor in componentes.values()) else "degradado"
    )
    return EstadoDependencias(estado=estado, componentes=componentes)
