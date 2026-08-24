"""Consultas de empresas sempre filtradas por associacao ativa."""

from uuid import UUID

from django.db.models import QuerySet

from apps.empresas.models import Empresa


def listar_empresas_permitidas(usuario) -> QuerySet[Empresa]:
    """Lista somente empresas vinculadas ativamente ao usuario."""
    return (
        Empresa.objects.filter(membros__usuario=usuario, membros__ativo=True)
        .distinct()
        .order_by("criado_em", "pk")
    )


def obter_empresa_permitida(usuario, empresa_id: UUID) -> Empresa:
    """Retorna uma empresa apenas quando o usuario possui associacao ativa."""
    return listar_empresas_permitidas(usuario).get(pk=empresa_id)
