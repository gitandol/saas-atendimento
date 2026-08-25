"""Testa uma configuracao de IA sem persistir credenciais temporarias."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.obter_empresa import autorizar_membro
from apps.ia.integrations.openai import ProviderOpenAI
from apps.ia.services.obter_provider import obter_provider


@dataclass(frozen=True)
class ResultadoTesteIA:
    """Informa o resultado publico e seguro de um teste de conexao."""

    sucesso: bool
    mensagem: str


def testar_configuracao(
    *, empresa: Empresa, ator: Usuario, chave_api: str, modelo: str
) -> ResultadoTesteIA:
    """Exige administrador e executa uma chamada curta sem salvar a chave."""
    membro = autorizar_membro(empresa=empresa, ator=ator)
    if membro.papel != MembroEmpresa.Papel.ADMINISTRADOR:
        raise PermissionDenied
    chave = chave_api.strip()
    provider = ProviderOpenAI(chave_api=chave) if chave else obter_provider(empresa)
    provider.gerar_resposta(
        [{"role": "user", "content": "Responda apenas OK."}], modelo
    )
    return ResultadoTesteIA(True, "Conexao com a OpenAI realizada com sucesso.")
