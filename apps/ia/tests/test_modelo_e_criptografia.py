"""Testes do modelo e da criptografia da configuracao de IA."""

import pytest
from django.db import IntegrityError

from apps.empresas.models import Empresa


@pytest.mark.django_db
def test_configuracao_e_unica_por_empresa_e_persiste_campos() -> None:
    """Impede configuracoes duplicadas e preserva os ajustes operacionais."""
    from apps.ia.models import ConfiguracaoIA

    empresa = Empresa.objects.create(nome="Empresa IA")
    configuracao = ConfiguracaoIA.objects.create(
        empresa=empresa,
        modelo="gpt-4.1-mini",
        nome_assistente="Lia",
        personalidade="Objetiva e cordial",
        mensagem_saudacao="Ola! Como posso ajudar?",
        mensagem_falha="Vou encaminhar seu atendimento.",
        respostas_automaticas_ativas=True,
    )

    assert configuracao.modelo == "gpt-4.1-mini"
    assert configuracao.nome_assistente == "Lia"
    assert configuracao.personalidade == "Objetiva e cordial"
    assert configuracao.mensagem_saudacao == "Ola! Como posso ajudar?"
    assert configuracao.mensagem_falha == "Vou encaminhar seu atendimento."
    assert configuracao.respostas_automaticas_ativas is True
    with pytest.raises(IntegrityError):
        ConfiguracaoIA.objects.create(empresa=empresa)


@pytest.mark.django_db
def test_chave_e_criptografada_em_repouso_e_ocultada_no_repr(settings) -> None:
    """Evita persistir ou representar a credencial OpenAI em texto puro."""
    from apps.ia.models import ConfiguracaoIA
    from apps.ia.services.criptografia import criptografar_chave, descriptografar_chave

    settings.IA_CHAVE_CRIPTOGRAFIA = "segredo-mestre-de-testes"
    chave = "sk-chave-super-secreta"
    criptografada = criptografar_chave(chave)
    empresa = Empresa.objects.create(nome="Empresa segura")
    configuracao = ConfiguracaoIA.objects.create(
        empresa=empresa,
        chave_api_criptografada=criptografada,
    )

    configuracao.refresh_from_db()
    assert configuracao.chave_api_criptografada != chave
    assert chave not in configuracao.chave_api_criptografada
    assert chave not in repr(configuracao)
    assert descriptografar_chave(configuracao.chave_api_criptografada) == chave
