"""Expoe a fronteira autenticada de reenvio manual."""

from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.whatsapp.api.schemas.reenvio_mensagem import (
    ReenvioMensagemErroSchema,
    ReenvioMensagemSaidaSchema,
)
from apps.whatsapp.services.enviar_mensagem import (
    ReenvioMensagemNaoPermitido,
    reenviar_mensagem,
)

router = Router(tags=["whatsapp"], auth=SessionAuth())


@router.post(
    "/whatsapp/mensagens/{mensagem_id}/reenviar",
    response={
        202: ReenvioMensagemSaidaSchema,
        403: ReenvioMensagemErroSchema,
        409: ReenvioMensagemErroSchema,
    },
)
def solicitar_reenvio(request: HttpRequest, mensagem_id: UUID):
    """Converte o UUID, resolve o tenant e delega a regra ao service."""
    try:
        empresa = exigir_empresa_ativa(request)
        mensagem = reenviar_mensagem(
            empresa=empresa,
            ator=request.user,
            mensagem_id=mensagem_id,
            correlacao=request.headers.get("X-Correlation-ID") or str(uuid4()),
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return Status(
            403,
            {"codigo": "permissao_negada", "mensagem": "Acesso negado."},
        )
    except ReenvioMensagemNaoPermitido:
        return Status(
            409,
            {
                "codigo": "reenvio_nao_permitido",
                "mensagem": "A mensagem nao esta elegivel para reenvio.",
            },
        )
    return Status(
        202,
        {"mensagem_id": mensagem.id, "status": mensagem.status},
    )
