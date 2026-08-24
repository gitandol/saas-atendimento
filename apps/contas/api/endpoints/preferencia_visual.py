"""Expoe a preferencia visual da sessao autenticada."""

from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.contas.api.schemas.comum import ErroSaidaSchema, erro
from apps.contas.api.schemas.preferencia_visual import (
    PreferenciaVisualEntradaSchema,
    PreferenciaVisualSaidaSchema,
)
from apps.contas.services.preferencia_visual import (
    atualizar_preferencia_visual,
    obter_preferencia_visual,
)

router = Router(tags=["preferencias"], auth=SessionAuth())


def _empresa_ativa(request: HttpRequest):
    """Retorna o tenant resolvido pelo middleware ou uma resposta de erro."""
    empresa = getattr(request, "empresa_ativa", None)
    if empresa is None:
        return Status(
            403,
            erro("empresa_ativa_ausente", "Nenhuma empresa ativa disponivel."),
        )
    return empresa


@router.get(
    "",
    response={200: PreferenciaVisualSaidaSchema, 403: ErroSaidaSchema},
)
def consultar_preferencia_visual(request: HttpRequest):
    """Consulta a preferencia visual efetiva na empresa ativa."""
    empresa = _empresa_ativa(request)
    if isinstance(empresa, Status):
        return empresa
    try:
        return obter_preferencia_visual(empresa=empresa, usuario=request.user)
    except PermissionDenied:
        return Status(403, erro("acesso_negado", "Acesso negado."))


@router.put(
    "",
    response={200: PreferenciaVisualSaidaSchema, 403: ErroSaidaSchema},
)
def alterar_preferencia_visual(
    request: HttpRequest,
    dados: PreferenciaVisualEntradaSchema,
):
    """Valida o contrato e delega persistencia e auditoria ao service."""
    empresa = _empresa_ativa(request)
    if isinstance(empresa, Status):
        return empresa
    try:
        return atualizar_preferencia_visual(
            empresa=empresa,
            usuario=request.user,
            tema=dados.tema,
            modo=dados.modo,
            origem="api",
            correlacao=request.headers.get("X-Correlation-ID") or str(uuid4()),
        )
    except PermissionDenied:
        return Status(403, erro("acesso_negado", "Acesso negado."))
