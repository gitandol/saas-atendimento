"""Expoe a restauracao administrativa de uma revisao."""

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.auditoria.api.schemas.historico import (
    ErroAuditoriaSchema,
    ItemHistoricoSchema,
)
from apps.auditoria.api.schemas.restauracao import RestauracaoEntradaSchema
from apps.auditoria.api.schemas.validacao import ErroValidacaoSchema
from apps.auditoria.services.restaurar_revisao import RevisaoNaoRestauravel
from apps.auditoria.services.restaurar_revisao_por_id import restaurar_revisao_por_id
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    PermissaoEmpresaNegada,
    exigir_administrador,
)

router = Router(tags=["auditoria"], auth=SessionAuth())


@router.post(
    "/revisoes/{revisao_id}/restaurar",
    response={
        200: ItemHistoricoSchema,
        403: ErroAuditoriaSchema,
        404: ErroAuditoriaSchema,
        409: ErroAuditoriaSchema,
        422: ErroValidacaoSchema,
    },
)
def restaurar(request: HttpRequest, revisao_id: int, dados: RestauracaoEntradaSchema):
    """Autoriza, delega a restauracao e traduz falhas de dominio."""
    try:
        membro = exigir_administrador(request)
        evento = restaurar_revisao_por_id(
            empresa=membro.empresa,
            revisao_id=revisao_id,
            ator=request.user,
            origem="api",
            correlacao=dados.correlacao,
        )
    except (EmpresaAtivaAusente, PermissaoEmpresaNegada):
        return Status(
            403,
            {"codigo": "permissao_negada", "mensagem": "Acesso negado."},
        )
    except ObjectDoesNotExist:
        return Status(
            404,
            {
                "codigo": "revisao_nao_encontrada",
                "mensagem": "Revisao nao encontrada.",
            },
        )
    except RevisaoNaoRestauravel:
        return Status(
            409,
            {
                "codigo": "revisao_incompativel",
                "mensagem": "Revisao nao pode ser restaurada.",
            },
        )
    return {
        "id": evento.pk,
        "revisao_id": evento.revisao_id,
        "revisao_numero": evento.revisao.numero,
        "tipo_objeto": evento.tipo_objeto,
        "objeto_id": evento.objeto_id,
        "acao": evento.acao,
        "campos_alterados": evento.campos_alterados,
        "ator_id": evento.ator_id,
        "origem": evento.origem,
        "correlacao": evento.correlacao,
        "criado_em": evento.criado_em,
    }
