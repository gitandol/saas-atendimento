"""Expoe liveness e dependencias em contratos independentes."""

from django.http import HttpRequest
from ninja import Router

from apps.nucleo.api.schemas.saude import (
    DependenciasSaidaSchema,
    SaudeSaidaSchema,
)
from apps.nucleo.services.verificacoes import verificar_dependencias
from apps.nucleo.services.verificar_saude import verificar_saude

router = Router(tags=["saude"])


@router.get("/saude", response=SaudeSaidaSchema)
def obter_saude(request: HttpRequest) -> dict[str, str]:  # noqa: ARG001
    """Converte a liveness local no contrato HTTP."""
    estado = verificar_saude()
    return {"estado": estado.estado}


@router.get("/saude/dependencias", response=DependenciasSaidaSchema)
def obter_dependencias(request: HttpRequest) -> dict[str, object]:  # noqa: ARG001
    """Publica dependencias degradadas sem alterar a liveness."""
    estado = verificar_dependencias()
    return {"estado": estado.estado, "componentes": estado.componentes}
