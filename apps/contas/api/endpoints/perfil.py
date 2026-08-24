"""Expoe perfis somente no escopo permitido ao usuario."""

from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.contas.api.schemas.comum import ErroSaidaSchema, erro
from apps.contas.api.schemas.perfil import PerfilSaidaSchema
from apps.contas.services.obter_perfil import obter_perfil
from apps.empresas.services.empresa_ativa import EmpresaAtivaAusente

router = Router(tags=["perfil"], auth=SessionAuth())


def _resolver_perfil(request: HttpRequest, empresa_id: UUID | None):
    """Delega a consulta e traduz falhas de isolamento para HTTP."""
    try:
        return obter_perfil(request, empresa_id)
    except EmpresaAtivaAusente:
        return Status(
            403,
            erro("empresa_ativa_ausente", "Nenhuma empresa ativa disponivel."),
        )
    except ObjectDoesNotExist:
        return Status(
            404,
            erro("perfil_nao_encontrado", "Perfil nao encontrado."),
        )


@router.get(
    "",
    response={200: PerfilSaidaSchema, 403: ErroSaidaSchema, 404: ErroSaidaSchema},
)
def obter_perfil_ativo(request: HttpRequest):
    """Retorna o perfil da empresa ativa resolvida pelo service."""
    return _resolver_perfil(request, None)


@router.get(
    "/{empresa_id}",
    response={200: PerfilSaidaSchema, 403: ErroSaidaSchema, 404: ErroSaidaSchema},
)
def obter_perfil_da_empresa(request: HttpRequest, empresa_id: UUID):
    """Retorna o perfil de uma empresa explicitamente permitida."""
    return _resolver_perfil(request, empresa_id)
