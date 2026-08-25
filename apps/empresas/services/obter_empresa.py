"""Consulta a configuracao empresarial com isolamento por tenant."""

from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import PermissionDenied

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


@dataclass(frozen=True)
class ConfiguracaoEmpresa:
    """Representa os dados empresariais usados pelas demais camadas."""

    nome: str
    segmento: str
    descricao: str
    horario_atendimento: str
    endereco: str
    telefone: str
    site: str
    instrucoes_atendimento: str
    atualizado_em: datetime


def autorizar_membro(*, empresa: Empresa, ator: Usuario) -> MembroEmpresa:
    """Exige associacao ativa do ator com a empresa informada."""
    membro = MembroEmpresa.objects.filter(
        empresa=empresa,
        usuario=ator,
        ativo=True,
    ).first()
    if membro is None:
        raise PermissionDenied
    return membro


def configuracao_da_empresa(empresa: Empresa) -> ConfiguracaoEmpresa:
    """Converte o model persistido no tipo de dominio publico."""
    return ConfiguracaoEmpresa(
        nome=empresa.nome,
        segmento=empresa.segmento,
        descricao=empresa.descricao,
        horario_atendimento=empresa.horario_atendimento,
        endereco=empresa.endereco,
        telefone=empresa.telefone,
        site=empresa.site,
        instrucoes_atendimento=empresa.instrucoes_atendimento,
        atualizado_em=empresa.atualizado_em,
    )


def obter_empresa(*, empresa: Empresa, ator: Usuario) -> ConfiguracaoEmpresa:
    """Retorna a configuracao atual somente a membro ativo do tenant."""
    autorizar_membro(empresa=empresa, ator=ator)
    empresa_atual = Empresa.objects.get(pk=empresa.pk)
    return configuracao_da_empresa(empresa_atual)
