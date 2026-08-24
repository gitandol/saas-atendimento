"""Fornece a verificacao local e deterministica de saude."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EstadoSaude:
    """Representa o estado interno do processo da aplicacao."""

    estado: str


def verificar_saude() -> EstadoSaude:
    """Retorna saude positiva sem acessar banco, Redis ou APIs externas."""
    return EstadoSaude(estado="ok")
