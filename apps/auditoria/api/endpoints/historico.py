"""Expoe o historico administrativo da empresa ativa."""

from dataclasses import asdict

from django.http import HttpRequest
from ninja import Query, Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.auditoria.api.schemas.historico import (
    ErroAuditoriaSchema,
    PaginaHistoricoSchema,
)
from apps.auditoria.services.consultar_historico import consultar_historico
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    PermissaoEmpresaNegada,
    exigir_administrador,
)

router = Router(tags=["auditoria"], auth=SessionAuth())


@router.get(
    "/historico",
    response={200: PaginaHistoricoSchema, 403: ErroAuditoriaSchema},
)
def obter_historico(
    request: HttpRequest,
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=100),
):
    """Autoriza administrador e devolve uma pagina sem snapshots."""
    try:
        membro = exigir_administrador(request)
    except (EmpresaAtivaAusente, PermissaoEmpresaNegada):
        return Status(403, {"codigo": "permissao_negada", "mensagem": "Acesso negado."})
    return asdict(
        consultar_historico(empresa=membro.empresa, pagina=pagina, tamanho=tamanho)
    )
