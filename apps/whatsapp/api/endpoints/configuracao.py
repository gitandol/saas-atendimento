"""Expoe configuracao e acoes da instancia da empresa ativa."""

from dataclasses import asdict
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.whatsapp.api.schemas.configuracao_whatsapp import (
    ConfiguracaoWhatsAppEntradaSchema,
    ConfiguracaoWhatsAppSaidaSchema,
    ErroWhatsAppSchema,
)
from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    InstanciaWhatsAppNaoEncontrada,
    LimiteWhatsAppExcedido,
    WhatsAppIndisponivel,
)
from apps.whatsapp.services.configurar_instancia import (
    ConfiguracaoWhatsAppInvalida,
    DadosConfiguracaoWhatsApp,
    atualizar_configuracao,
    conectar_instancia,
    desconectar_instancia,
    obter_configuracao,
)

router = Router(tags=["whatsapp"], auth=SessionAuth())


def correlacao(request: HttpRequest) -> str:
    """Reaproveita ou cria o identificador seguro da operacao."""
    valor = request.headers.get("X-Correlation-ID", "")
    return valor if 0 < len(valor) <= 80 else str(uuid4())


def erro(status: int, codigo: str, mensagem: str) -> Status:
    """Constroi uma falha HTTP publica sem detalhes externos."""
    return Status(status, {"codigo": codigo, "mensagem": mensagem})


def permissao() -> Status:
    """Oculta detalhes de associacao e empresa ativa."""
    return erro(403, "permissao_negada", "Acesso negado.")


def erro_provider(excecao: Exception) -> Status:
    """Traduz excecoes externas no contrato comum sem vazar detalhes."""
    if isinstance(excecao, CredencialWhatsAppInvalida):
        return erro(400, "credencial_whatsapp_invalida", "Verifique a credencial.")
    if isinstance(excecao, InstanciaWhatsAppNaoEncontrada):
        return erro(404, "instancia_nao_encontrada", "Instancia nao encontrada.")
    if isinstance(excecao, LimiteWhatsAppExcedido):
        return erro(429, "limite_whatsapp_excedido", "Limite externo atingido.")
    return erro(503, "whatsapp_indisponivel", "WhatsApp indisponivel no momento.")


@router.get(
    "/whatsapp/configuracao",
    response={200: ConfiguracaoWhatsAppSaidaSchema, 403: ErroWhatsAppSchema},
)
def consultar_configuracao(request: HttpRequest):
    """Delega a consulta segura da configuracao da empresa ativa."""
    try:
        empresa = exigir_empresa_ativa(request)
        return asdict(obter_configuracao(empresa=empresa, ator=request.user))
    except (EmpresaAtivaAusente, PermissionDenied):
        return permissao()


@router.put(
    "/whatsapp/configuracao",
    response={
        200: ConfiguracaoWhatsAppSaidaSchema,
        400: ErroWhatsAppSchema,
        403: ErroWhatsAppSchema,
    },
)
def substituir_configuracao(
    request: HttpRequest, dados: ConfiguracaoWhatsAppEntradaSchema
):
    """Converte o schema em dados de dominio e delega a atualizacao."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = atualizar_configuracao(
            empresa=empresa,
            ator=request.user,
            dados=DadosConfiguracaoWhatsApp(**dados.model_dump()),
            correlacao=correlacao(request),
        )
        return asdict(resultado)
    except (EmpresaAtivaAusente, PermissionDenied):
        return permissao()
    except ConfiguracaoWhatsAppInvalida as excecao:
        return erro(400, "configuracao_whatsapp_invalida", str(excecao))


def _alterar_conexao(request: HttpRequest, operacao):
    """Compartilha autorizacao e traducao das acoes conectar/desconectar."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = operacao(
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


@router.post(
    "/whatsapp/conectar",
    response={
        200: ConfiguracaoWhatsAppSaidaSchema,
        400: ErroWhatsAppSchema,
        403: ErroWhatsAppSchema,
        404: ErroWhatsAppSchema,
        429: ErroWhatsAppSchema,
        503: ErroWhatsAppSchema,
    },
)
def conectar(request: HttpRequest):
    """Delega a criacao ou inicializacao da instancia Evolution."""
    return _alterar_conexao(request, conectar_instancia)


@router.post(
    "/whatsapp/desconectar",
    response={
        200: ConfiguracaoWhatsAppSaidaSchema,
        400: ErroWhatsAppSchema,
        403: ErroWhatsAppSchema,
        404: ErroWhatsAppSchema,
        429: ErroWhatsAppSchema,
        503: ErroWhatsAppSchema,
    },
)
def desconectar(request: HttpRequest):
    """Delega o encerramento da sessao Evolution atual."""
    return _alterar_conexao(request, desconectar_instancia)
