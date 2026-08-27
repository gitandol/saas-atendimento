"""Lista conversas visiveis de uma empresa ativa."""

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Conversa
from apps.atendimento.services.conversas import conversa_para_dto
from apps.empresas.models import Empresa


def listar_conversas(*, empresa: Empresa) -> list[ConversaDTO]:
    """Retorna DTOs ordenados sem expor QuerySet ou contatos excluidos."""
    consulta = (
        Conversa.objects.filter(
            empresa=empresa,
            contato__empresa=empresa,
            contato__excluido_em__isnull=True,
        )
        .select_related("contato")
        .order_by("-atualizado_em", "-id")
    )
    return [conversa_para_dto(conversa) for conversa in consulta]
