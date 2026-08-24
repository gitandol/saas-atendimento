"""Consulta metadados de auditoria isolados por empresa."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.auditoria.models import EventoAuditoria
from apps.empresas.models import Empresa


@dataclass(frozen=True, slots=True)
class ItemHistorico:
    """Representa metadados publicos de um evento sem seus snapshots."""

    id: UUID
    revisao_id: int
    revisao_numero: int
    tipo_objeto: str
    objeto_id: str
    acao: str
    campos_alterados: list[str]
    ator_id: UUID | None
    origem: str
    correlacao: str
    criado_em: datetime


@dataclass(frozen=True, slots=True)
class PaginaHistorico:
    """Agrupa uma pagina e a contagem total do historico."""

    itens: list[ItemHistorico]
    pagina: int
    tamanho: int
    total: int


def consultar_historico(
    *, empresa: Empresa, pagina: int, tamanho: int
) -> PaginaHistorico:
    """Retorna somente eventos da empresa dentro da janela solicitada."""
    consulta = EventoAuditoria.objects.filter(empresa=empresa).select_related("revisao")
    total = consulta.count()
    inicio = (pagina - 1) * tamanho
    eventos = consulta[inicio : inicio + tamanho]
    itens = [
        ItemHistorico(
            id=evento.pk,
            revisao_id=evento.revisao_id,
            revisao_numero=evento.revisao.numero,
            tipo_objeto=evento.tipo_objeto,
            objeto_id=evento.objeto_id,
            acao=evento.acao,
            campos_alterados=evento.campos_alterados,
            ator_id=evento.ator_id,
            origem=evento.origem,
            correlacao=evento.correlacao,
            criado_em=evento.criado_em,
        )
        for evento in eventos
    ]
    return PaginaHistorico(itens=itens, pagina=pagina, tamanho=tamanho, total=total)
