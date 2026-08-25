"""Expoe o CRUD de perguntas frequentes da empresa ativa."""

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
from apps.ia.api.schemas.pergunta_frequente import (
    PaginaPerguntasFrequentesSchema,
    PerguntaFrequenteEntradaSchema,
    PerguntaFrequenteSaidaSchema,
)
from apps.ia.services.gerenciar_conhecimento import (
    DadosPerguntaFrequente,
    atualizar_pergunta_frequente,
    criar_pergunta_frequente,
    excluir_pergunta_frequente,
    listar_perguntas_frequentes,
)

router = Router(tags=["ia-faq"], auth=SessionAuth())


def _correlacao(request: HttpRequest) -> str:
    """Reaproveita ou cria o identificador seguro da operacao."""
    valor = request.headers.get("X-Correlation-ID", "")
    return valor if 0 < len(valor) <= 80 else str(uuid4())


def _permissao() -> Status:
    """Padroniza falhas de autorizacao sem revelar associacoes."""
    return Status(403, {"codigo": "permissao_negada", "mensagem": "Acesso negado."})


def _nao_encontrada() -> Status:
    """Oculta a existencia de objetos de outros tenants."""
    return Status(
        404,
        {"codigo": "nao_encontrado", "mensagem": "Pergunta frequente nao encontrada."},
    )


@router.get(
    "/ia/perguntas-frequentes",
    response={200: PaginaPerguntasFrequentesSchema, 403: ErroIASchema},
)
def consultar_perguntas(
    request: HttpRequest,
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=100),
):
    """Lista FAQ do tenant para qualquer membro ativo."""
    try:
        empresa = exigir_empresa_ativa(request)
        return asdict(
            listar_perguntas_frequentes(
                empresa=empresa, ator=request.user, pagina=pagina, tamanho=tamanho
            )
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()


@router.post(
    "/ia/perguntas-frequentes",
    response={201: PerguntaFrequenteSaidaSchema, 403: ErroIASchema},
)
def adicionar_pergunta(request: HttpRequest, dados: PerguntaFrequenteEntradaSchema):
    """Delega a criacao administrativa de uma FAQ."""
    try:
        empresa = exigir_empresa_ativa(request)
        resultado = criar_pergunta_frequente(
            empresa=empresa,
            ator=request.user,
            dados=DadosPerguntaFrequente(**dados.model_dump()),
            correlacao=_correlacao(request),
        )
        return Status(201, asdict(resultado))
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()


@router.put(
    "/ia/perguntas-frequentes/{pergunta_id}",
    response={200: PerguntaFrequenteSaidaSchema, 403: ErroIASchema, 404: ErroIASchema},
)
def substituir_pergunta(
    request: HttpRequest, pergunta_id: int, dados: PerguntaFrequenteEntradaSchema
):
    """Delega edicao, ativacao e ordenacao de uma FAQ."""
    try:
        empresa = exigir_empresa_ativa(request)
        return asdict(
            atualizar_pergunta_frequente(
                empresa=empresa,
                ator=request.user,
                pergunta_id=pergunta_id,
                dados=DadosPerguntaFrequente(**dados.model_dump()),
                correlacao=_correlacao(request),
            )
        )
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()
    except ObjectDoesNotExist:
        return _nao_encontrada()


@router.delete(
    "/ia/perguntas-frequentes/{pergunta_id}",
    response={204: None, 403: ErroIASchema, 404: ErroIASchema},
)
def remover_pergunta(request: HttpRequest, pergunta_id: int):
    """Delega a exclusao logica administrativa de uma FAQ."""
    try:
        empresa = exigir_empresa_ativa(request)
        excluir_pergunta_frequente(
            empresa=empresa,
            ator=request.user,
            pergunta_id=pergunta_id,
            correlacao=_correlacao(request),
        )
        return Status(204, None)
    except (EmpresaAtivaAusente, PermissionDenied):
        return _permissao()
    except ObjectDoesNotExist:
        return _nao_encontrada()
