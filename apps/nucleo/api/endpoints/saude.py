"""Expoe o estado basico da aplicacao sem consultar dependencias externas."""

from django.http import HttpRequest
from ninja import Router

from apps.nucleo.api.schemas.saude import SaudeSaidaSchema
from apps.nucleo.services.verificar_saude import verificar_saude

router = Router(tags=["saude"])


@router.get("/saude", response=SaudeSaidaSchema)
def obter_saude(request: HttpRequest) -> dict[str, str]:  # noqa: ARG001
    """Converte o resultado de dominio no contrato HTTP de saude."""
    estado = verificar_saude()
    return {"estado": estado.estado}
