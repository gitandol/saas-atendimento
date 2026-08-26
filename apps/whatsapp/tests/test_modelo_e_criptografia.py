"""Testes do modelo e da protecao de credenciais do WhatsApp."""

import pytest
from django.db import IntegrityError

from apps.empresas.models import Empresa


@pytest.mark.django_db
def test_configuracao_whatsapp_e_unica_por_empresa_e_persiste_campos() -> None:
    """Impede duas instancias por empresa e preserva o estado operacional."""
    from apps.whatsapp.integrations.protocolos import EstadoConexao
    from apps.whatsapp.models import ConfiguracaoWhatsApp

    empresa = Empresa.objects.create(nome="Empresa WhatsApp")
    configuracao = ConfiguracaoWhatsApp.objects.create(
        empresa=empresa,
        url_base="https://evolution.example.com",
        nome_instancia="empresa-whatsapp",
        chave_api_criptografada="cifra",
        ativo=True,
        estado=EstadoConexao.AGUARDANDO_QR,
    )

    assert configuracao.url_base == "https://evolution.example.com"
    assert configuracao.nome_instancia == "empresa-whatsapp"
    assert configuracao.ativo is True
    assert configuracao.estado == EstadoConexao.AGUARDANDO_QR
    with pytest.raises(IntegrityError):
        ConfiguracaoWhatsApp.objects.create(
            empresa=empresa,
            url_base="https://outra.example.com",
            nome_instancia="duplicada",
        )


@pytest.mark.django_db
def test_chave_e_criptografada_em_repouso_e_ocultada_no_repr(settings) -> None:
    """Evita persistir ou representar a credencial Evolution em texto puro."""
    from apps.whatsapp.models import ConfiguracaoWhatsApp
    from apps.whatsapp.services.criptografia import (
        criptografar_chave,
        descriptografar_chave,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "segredo-mestre-compartilhado"
    chave = "evolution-chave-super-secreta"
    criptografada = criptografar_chave(chave)
    configuracao = ConfiguracaoWhatsApp.objects.create(
        empresa=Empresa.objects.create(nome="Empresa segura WhatsApp"),
        url_base="https://evolution.example.com",
        nome_instancia="segura",
        chave_api_criptografada=criptografada,
    )

    configuracao.refresh_from_db()
    assert configuracao.chave_api_criptografada != chave
    assert chave not in configuracao.chave_api_criptografada
    assert chave not in repr(configuracao)
    assert descriptografar_chave(configuracao.chave_api_criptografada) == chave
