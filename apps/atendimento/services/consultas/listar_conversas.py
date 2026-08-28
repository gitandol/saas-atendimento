"""Lista conversas visiveis de uma empresa ativa."""

from django.db.models import Q

from apps.atendimento.dto import ConversaDTO
from apps.atendimento.models import Conversa
from apps.atendimento.services.conversas import conversa_para_dto
from apps.empresas.models import Empresa


def listar_conversas(
    *,
    empresa: Empresa,
    busca: str = "",
    filtro: str = "ABERTAS",
) -> list[ConversaDTO]:
    """Retorna conversas filtradas por atividade sem expor QuerySet."""
    consulta = (
        Conversa.objects.filter(
            empresa=empresa,
            contato__empresa=empresa,
            contato__excluido_em__isnull=True,
        )
        .select_related("contato", "atendente", "ultima_mensagem")
        .order_by("-atualizado_em", "-id")
    )
    filtro_normalizado = filtro.upper()
    if filtro_normalizado == "FINALIZADAS":
        consulta = consulta.filter(estado=Conversa.Estado.FINALIZADA)
    else:
        consulta = consulta.filter(estado=Conversa.Estado.ABERTA)
        if filtro_normalizado in {Conversa.Modo.IA, Conversa.Modo.HUMANO}:
            consulta = consulta.filter(modo=filtro_normalizado)
    termo = busca.strip()
    if termo:
        filtro_busca = Q(contato__nome__icontains=termo)
        numero = "".join(caractere for caractere in termo if caractere.isdigit())
        if numero:
            filtro_busca |= Q(contato__numero_normalizado__icontains=numero)
        consulta = consulta.filter(filtro_busca)
    return [conversa_para_dto(conversa) for conversa in consulta]
