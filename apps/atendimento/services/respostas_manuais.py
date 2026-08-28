"""Cria respostas manuais e as entrega ao pipeline do WhatsApp."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.atendimento.dto import MensagemDTO
from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.services.mensagens import registrar_mensagem
from apps.contas.models import Usuario
from apps.empresas.models import Empresa
from apps.empresas.services.obter_empresa import autorizar_membro


@transaction.atomic
def enviar_resposta_manual(
    *,
    empresa: Empresa,
    conversa_id: UUID,
    texto: str,
    ator: Usuario,
    correlacao: str,
) -> MensagemDTO:
    """Persiste uma saida pendente autorizada e solicita o envio assíncrono."""
    autorizar_membro(empresa=empresa, ator=ator)
    conversa = Conversa.objects.select_for_update().get(
        pk=conversa_id,
        empresa=empresa,
    )
    if conversa.estado != Conversa.Estado.ABERTA:
        raise ValidationError({"conversa": "A conversa esta finalizada."})
    if conversa.modo != Conversa.Modo.HUMANO or conversa.atendente_id != ator.id:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    texto_normalizado = texto.strip()
    if not texto_normalizado or len(texto_normalizado) > 4096:
        raise ValidationError({"texto": "Informe entre 1 e 4096 caracteres."})
    mensagem = registrar_mensagem(
        empresa=empresa,
        conversa_id=conversa_id,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.ATENDENTE,
        texto=texto_normalizado,
        identificador_externo="",
        status=Mensagem.Status.PENDENTE,
        ator=ator,
        origem="api_caixa_entrada",
        correlacao=correlacao,
    )
    from apps.whatsapp.services.enviar_mensagem import solicitar_envio

    solicitar_envio(mensagem.id, correlacao)
    return mensagem
