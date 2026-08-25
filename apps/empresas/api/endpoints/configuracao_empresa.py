"""Expoe a configuracao da empresa ativa."""

from dataclasses import asdict
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.empresas.api.schemas.configuracao_empresa import (
    EmpresaEntradaSchema,
    EmpresaSaidaSchema,
    ErroEmpresaSchema,
)
from apps.empresas.services.atualizar_empresa import (
    ConflitoAtualizacaoEmpresa,
    DadosAtualizacaoEmpresa,
    atualizar_empresa,
)
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.empresas.services.obter_empresa import obter_empresa

router = Router(tags=["empresa"], auth=SessionAuth())


def _erro_permissao() -> Status:
    """Padroniza a resposta que nao revela detalhes de associacoes."""
    return Status(
        403,
        {"codigo": "permissao_negada", "mensagem": "Acesso negado."},
    )


@router.get(
    "/empresa",
    response={200: EmpresaSaidaSchema, 403: ErroEmpresaSchema},
)
def consultar_empresa(request: HttpRequest):
    """Resolve a empresa ativa e delega a consulta ao service."""
    try:
        empresa = exigir_empresa_ativa(request)
        configuracao = obter_empresa(empresa=empresa, ator=request.user)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _erro_permissao()
    return asdict(configuracao)


@router.put(
    "/empresa",
    response={
        200: EmpresaSaidaSchema,
        403: ErroEmpresaSchema,
        409: ErroEmpresaSchema,
    },
)
def substituir_empresa(request: HttpRequest, dados: EmpresaEntradaSchema):
    """Converte o payload em dados de dominio e traduz falhas esperadas."""
    try:
        empresa = exigir_empresa_ativa(request)
        configuracao = atualizar_empresa(
            empresa=empresa,
            dados=DadosAtualizacaoEmpresa(**dados.model_dump()),
            ator=request.user,
            correlacao=request.headers.get("X-Correlation-ID") or str(uuid4()),
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _erro_permissao()
    except ConflitoAtualizacaoEmpresa as erro:
        return Status(
            409,
            {"codigo": "versao_obsoleta", "mensagem": str(erro)},
        )
    return asdict(configuracao)
