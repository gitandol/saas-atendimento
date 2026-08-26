"""Expoe o estado normalizado da instancia da empresa ativa."""

from dataclasses import asdict

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from ninja import Router
from ninja.security import SessionAuth

from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.whatsapp.api.endpoints.configuracao import (
    correlacao,
    erro_provider,
    permissao,
)
from apps.whatsapp.api.schemas.configuracao_whatsapp import (
    ConfiguracaoWhatsAppSaidaSchema,
    ErroWhatsAppSchema,
)
from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    InstanciaWhatsAppNaoEncontrada,
    LimiteWhatsAppExcedido,
    WhatsAppIndisponivel,
)
from apps.whatsapp.services.consultar_conexao import consultar_estado

router = Router(tags=["whatsapp"], auth=SessionAuth())


@router.get(
    "/whatsapp/estado",
    response={
        200: ConfiguracaoWhatsAppSaidaSchema,
        400: ErroWhatsAppSchema,
        403: ErroWhatsAppSchema,
        404: ErroWhatsAppSchema,
        429: ErroWhatsAppSchema,
        503: ErroWhatsAppSchema,
    },
)
def estado_conexao(request: HttpRequest):
    """Delega a consulta externa e publica o estado normalizado."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = consultar_estado(
            empresa=empresa,
            ator=request.user,
            correlacao=correlacao(request),
        )
        return asdict(resultado)
    except (EmpresaAtivaAusente, PermissionDenied):
        return permissao()
    except (
        CredencialWhatsAppInvalida,
        InstanciaWhatsAppNaoEncontrada,
        LimiteWhatsAppExcedido,
        WhatsAppIndisponivel,
    ) as excecao:
        return erro_provider(excecao)
