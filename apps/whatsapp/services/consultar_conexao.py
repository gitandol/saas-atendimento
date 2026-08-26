"""Consulta estado e QR Code da instancia sem persistir dados temporarios."""

from django.db import transaction

from apps.contas.models import Usuario
from apps.empresas.models import Empresa
from apps.empresas.services.obter_empresa import autorizar_membro
from apps.whatsapp.integrations.protocolos import InstanciaWhatsAppNaoEncontrada
from apps.whatsapp.models import ConfiguracaoWhatsApp
from apps.whatsapp.services.configurar_instancia import (
    ConfiguracaoWhatsAppPublica,
    _obter_provider,
    _publicar,
    _registrar_estado,
)


@transaction.atomic
def consultar_estado(
    *, empresa: Empresa, ator: Usuario, correlacao: str
) -> ConfiguracaoWhatsAppPublica:
    """Consulta o fornecedor e audita somente uma transicao de estado."""
    autorizar_membro(empresa=empresa, ator=ator)
    configuracao = (
        ConfiguracaoWhatsApp.objects.select_for_update().filter(empresa=empresa).first()
    )
    if configuracao is None:
        raise InstanciaWhatsAppNaoEncontrada("Configure uma instancia de WhatsApp.")
    estado = _obter_provider(empresa).consultar_estado()
    if configuracao.estado == estado:
        return _publicar(configuracao)
    return _registrar_estado(
        configuracao=configuracao,
        empresa=empresa,
        ator=ator,
        correlacao=correlacao,
        ativo=configuracao.ativo,
        estado=estado,
    )


def obter_qrcode(*, empresa: Empresa, ator: Usuario) -> str:
    """Devolve o QR Code temporario sem gravar model ou auditoria."""
    autorizar_membro(empresa=empresa, ator=ator)
    return _obter_provider(empresa).obter_qrcode()
