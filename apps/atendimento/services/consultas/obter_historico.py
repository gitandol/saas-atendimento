"""Obtem o historico cronologico de uma conversa do tenant."""

from uuid import UUID

from apps.atendimento.dto import MensagemDTO
from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.services.mensagens import mensagem_para_dto
from apps.empresas.models import Empresa


def obter_historico(*, empresa: Empresa, conversa_id: UUID) -> list[MensagemDTO]:
    """Retorna DTOs em ordem estavel depois de validar o isolamento."""
    Conversa.objects.get(pk=conversa_id, empresa=empresa)
    consulta = Mensagem.objects.filter(
        empresa=empresa,
        conversa_id=conversa_id,
    ).order_by("criado_em", "id")
    return [mensagem_para_dto(mensagem) for mensagem in consulta]
