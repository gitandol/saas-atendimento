"""Expoe o QR Code temporario da instancia da empresa ativa."""

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, JsonResponse
from ninja import Router
from ninja.security import SessionAuth

from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.whatsapp.api.endpoints.configuracao import erro_provider, permissao
from apps.whatsapp.api.schemas.configuracao_whatsapp import (
    ErroWhatsAppSchema,
    QRCodeWhatsAppSaidaSchema,
)
from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    InstanciaWhatsAppNaoEncontrada,
    LimiteWhatsAppExcedido,
    WhatsAppIndisponivel,
)
from apps.whatsapp.services.consultar_conexao import obter_qrcode

router = Router(tags=["whatsapp"], auth=SessionAuth())


@router.get(
    "/whatsapp/qrcode",
    response={
        200: QRCodeWhatsAppSaidaSchema,
        400: ErroWhatsAppSchema,
        403: ErroWhatsAppSchema,
        404: ErroWhatsAppSchema,
        429: ErroWhatsAppSchema,
        503: ErroWhatsAppSchema,
    },
)
def consultar_qrcode(request: HttpRequest):
    """Delega a leitura do QR Code sem persistir seu conteudo."""
    try:
        empresa = exigir_empresa_ativa(request)
        qrcode = obter_qrcode(empresa=empresa, ator=request.user)
        resposta = JsonResponse({"qrcode": qrcode, "expira_em_segundos": 60})
        resposta["Cache-Control"] = "no-store, private"
        resposta["Pragma"] = "no-cache"
        return resposta
    except (EmpresaAtivaAusente, PermissionDenied):
        return permissao()
    except (
        CredencialWhatsAppInvalida,
        InstanciaWhatsAppNaoEncontrada,
        LimiteWhatsAppExcedido,
        WhatsAppIndisponivel,
    ) as excecao:
        return erro_provider(excecao)
