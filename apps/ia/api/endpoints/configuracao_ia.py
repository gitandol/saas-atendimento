"""Expoe configuracao e teste da IA da empresa ativa."""

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
from apps.ia.api.schemas.configuracao_ia import (
    ConfiguracaoIAEntradaSchema,
    ConfiguracaoIASaidaSchema,
    ErroIASchema,
    TesteIAEntradaSchema,
    TesteIASaidaSchema,
)
from apps.ia.integrations.protocolos import (
    CredencialIAInvalida,
    IAIndisponivel,
    LimiteIAExcedido,
)
from apps.ia.services.configuracao import (
    ConflitoAtualizacaoIA,
    DadosConfiguracaoIA,
    atualizar_configuracao,
    obter_configuracao,
    remover_chave,
)
from apps.ia.services.testar_configuracao import testar_configuracao

router = Router(tags=["ia"], auth=SessionAuth())


def _correlacao(request: HttpRequest) -> str:
    """Reaproveita ou cria o identificador seguro da operacao."""
    valor = request.headers.get("X-Correlation-ID", "")
    return valor if 0 < len(valor) <= 80 else str(uuid4())


def _erro(status: int, codigo: str, mensagem: str) -> Status:
    """Constroi uma falha HTTP publica sem detalhes externos."""
    return Status(status, {"codigo": codigo, "mensagem": mensagem})


def _permissao() -> Status:
    """Oculta detalhes de associacao e empresa ativa."""
    return _erro(403, "permissao_negada", "Acesso negado.")


@router.get(
    "/ia/configuracao", response={200: ConfiguracaoIASaidaSchema, 403: ErroIASchema}
)
def consultar_configuracao(request: HttpRequest):
    """Delega a consulta segura da configuracao da empresa ativa."""
    try:
        empresa = exigir_empresa_ativa(request)
        return asdict(obter_configuracao(empresa=empresa, ator=request.user))
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()


@router.put(
    "/ia/configuracao",
    response={200: ConfiguracaoIASaidaSchema, 403: ErroIASchema, 409: ErroIASchema},
)
def substituir_configuracao(request: HttpRequest, dados: ConfiguracaoIAEntradaSchema):
    """Converte o schema em dados de dominio e delega a atualizacao."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = atualizar_configuracao(
            empresa=empresa,
            ator=request.user,
            dados=DadosConfiguracaoIA(**dados.model_dump()),
            correlacao=_correlacao(request),
        )
        return asdict(resultado)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()
    except ConflitoAtualizacaoIA as erro:
        return _erro(409, "versao_obsoleta", str(erro))


@router.delete(
    "/ia/configuracao/chave",
    response={200: ConfiguracaoIASaidaSchema, 403: ErroIASchema},
)
def excluir_chave(request: HttpRequest):
    """Delega a remocao explicita da credencial da empresa ativa."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = remover_chave(
            empresa=empresa, ator=request.user, correlacao=_correlacao(request)
        )
        return asdict(resultado)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()


@router.post(
    "/ia/teste",
    response={
        200: TesteIASaidaSchema,
        400: ErroIASchema,
        403: ErroIASchema,
        429: ErroIASchema,
        503: ErroIASchema,
    },
)
def testar_conexao(request: HttpRequest, dados: TesteIAEntradaSchema):
    """Delega o teste e traduz apenas falhas de dominio conhecidas."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = testar_configuracao(
            empresa=empresa,
            ator=request.user,
            chave_api=dados.chave_api,
            modelo=dados.modelo,
        )
        return asdict(resultado)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()
    except CredencialIAInvalida:
        return _erro(400, "credencial_ia_invalida", "Verifique a credencial de IA.")
    except LimiteIAExcedido:
        return _erro(429, "limite_ia_excedido", "O limite da OpenAI foi atingido.")
    except IAIndisponivel:
        return _erro(503, "ia_indisponivel", "A OpenAI esta indisponivel no momento.")
