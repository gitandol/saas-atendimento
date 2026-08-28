"""Obtem o historico cronologico de uma conversa do tenant."""

from uuid import UUID

from django.db.models import Q

from apps.atendimento.dto import MensagemDTO
from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.services.mensagens import mensagem_para_dto
from apps.empresas.models import Empresa


def obter_historico(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    cursor: UUID | None = None,
    depois_de: UUID | None = None,
    limite: int | None = None,
) -> list[MensagemDTO]:
    """Retorna uma janela cronologica estavel depois de validar o isolamento."""
    Conversa.objects.get(pk=conversa_id, empresa=empresa)
    consulta = Mensagem.objects.filter(
        empresa=empresa,
        conversa_id=conversa_id,
    )
    if cursor is not None:
        ancora = consulta.get(pk=cursor)
        consulta = consulta.filter(
            Q(criado_em__lt=ancora.criado_em)
            | Q(criado_em=ancora.criado_em, id__lt=ancora.id)
        )
    if depois_de is not None:
        ancora = consulta.model.objects.get(
            pk=depois_de,
            empresa=empresa,
            conversa_id=conversa_id,
        )
        consulta = consulta.filter(
            Q(criado_em__gt=ancora.criado_em)
            | Q(criado_em=ancora.criado_em, id__gt=ancora.id)
        )
        ordenadas = consulta.order_by("criado_em", "id")
        if limite is not None:
            ordenadas = ordenadas[:limite]
        return [mensagem_para_dto(mensagem) for mensagem in ordenadas]
    if limite is None:
        ordenadas = consulta.order_by("criado_em", "id")
        return [mensagem_para_dto(mensagem) for mensagem in ordenadas]
    recentes = list(consulta.order_by("-criado_em", "-id")[:limite])
    recentes.reverse()
    return [mensagem_para_dto(mensagem) for mensagem in recentes]
