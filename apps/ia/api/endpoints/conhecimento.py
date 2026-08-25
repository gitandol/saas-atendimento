"""Expoe o CRUD de documentos textuais da empresa ativa."""

from dataclasses import asdict
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpRequest
from ninja import Query, Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.ia.api.schemas.configuracao_ia import ErroIASchema
from apps.ia.api.schemas.documento_textual import (
    DocumentoTextualEntradaSchema,
    DocumentoTextualSaidaSchema,
    PaginaDocumentosSchema,
)
from apps.ia.services.gerenciar_conhecimento import (
    DadosDocumentoTextual,
    atualizar_documento,
    criar_documento,
    excluir_documento,
    listar_documentos,
)

router = Router(tags=["ia-conhecimento"], auth=SessionAuth())


def _correlacao(request: HttpRequest) -> str:
    """Reaproveita ou cria o identificador seguro da operacao."""
    valor = request.headers.get("X-Correlation-ID", "")
    return valor if 0 < len(valor) <= 80 else str(uuid4())


def _permissao() -> Status:
    """Padroniza falhas de autorizacao sem revelar associacoes."""
    return Status(403, {"codigo": "permissao_negada", "mensagem": "Acesso negado."})


def _nao_encontrado() -> Status:
    """Oculta a existencia de objetos de outros tenants."""
    return Status(
        404, {"codigo": "nao_encontrado", "mensagem": "Conhecimento nao encontrado."}
    )


@router.get(
    "/ia/conhecimentos", response={200: PaginaDocumentosSchema, 403: ErroIASchema}
)
def consultar_documentos(
    request: HttpRequest,
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=100),
):
    """Lista documentos do tenant para qualquer membro ativo."""
    try:
        empresa = exigir_empresa_ativa(request)
        return asdict(
            listar_documentos(
                empresa=empresa, ator=request.user, pagina=pagina, tamanho=tamanho
            )
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()


@router.post(
    "/ia/conhecimentos", response={201: DocumentoTextualSaidaSchema, 403: ErroIASchema}
)
def adicionar_documento(request: HttpRequest, dados: DocumentoTextualEntradaSchema):
    """Delega a criacao administrativa de um documento."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = criar_documento(
            empresa=empresa,
            ator=request.user,
            dados=DadosDocumentoTextual(**dados.model_dump()),
            correlacao=_correlacao(request),
        )
        return Status(201, asdict(resultado))
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()


@router.put(
    "/ia/conhecimentos/{documento_id}",
    response={200: DocumentoTextualSaidaSchema, 403: ErroIASchema, 404: ErroIASchema},
)
def substituir_documento(
    request: HttpRequest, documento_id: int, dados: DocumentoTextualEntradaSchema
):
    """Delega edicao, ativacao e ordenacao de um documento."""
    try:
        empresa = exigir_empresa_ativa(request)
        return asdict(
            atualizar_documento(
                empresa=empresa,
                ator=request.user,
                documento_id=documento_id,
                dados=DadosDocumentoTextual(**dados.model_dump()),
                correlacao=_correlacao(request),
            )
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()
    except ObjectDoesNotExist:
        return _nao_encontrado()


@router.delete(
    "/ia/conhecimentos/{documento_id}",
    response={204: None, 403: ErroIASchema, 404: ErroIASchema},
)
def remover_documento(request: HttpRequest, documento_id: int):
    """Delega a exclusao logica administrativa de um documento."""
    try:
        empresa = exigir_empresa_ativa(request)
        excluir_documento(
            empresa=empresa,
            ator=request.user,
            documento_id=documento_id,
            correlacao=_correlacao(request),
        )
        return Status(204, None)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()
    except ObjectDoesNotExist:
        return _nao_encontrado()
