"""Seleciona o provider de IA configurado para uma empresa."""

from apps.empresas.models import Empresa
from apps.ia.integrations.openai import ProviderOpenAI
from apps.ia.integrations.protocolos import CredencialIAInvalida, ProviderIA
from apps.ia.models import ConfiguracaoIA
from apps.ia.services.criptografia import (
    ChaveCriptografadaInvalida,
    descriptografar_chave,
)


def obter_provider(empresa: Empresa) -> ProviderIA:
    """Constroi o provider OpenAI sem expor a credencial ao consumidor."""
    configuracao = ConfiguracaoIA.objects.filter(empresa=empresa).first()
    if configuracao is None or not configuracao.chave_api_criptografada:
        raise CredencialIAInvalida("Configure uma credencial de IA.")
    try:
        chave = descriptografar_chave(configuracao.chave_api_criptografada)
    except ChaveCriptografadaInvalida as erro:
        raise CredencialIAInvalida(
            "A credencial de IA precisa ser configurada novamente."
        ) from erro
    return ProviderOpenAI(chave_api=chave)
