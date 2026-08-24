"""Resolve revisoes por identificador dentro da empresa ativa."""

from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
from apps.auditoria.services.restaurar_revisao import restaurar_revisao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


def restaurar_revisao_por_id(
    *,
    empresa: Empresa,
    revisao_id: int,
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> EventoAuditoria:
    """Busca a revisao no tenant antes de executar sua restauracao."""
    revisao = RevisaoObjeto.objects.get(pk=revisao_id, empresa=empresa)
    return restaurar_revisao(
        empresa=empresa,
        revisao=revisao,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
