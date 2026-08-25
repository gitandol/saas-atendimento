"""Atualiza a configuracao empresarial com concorrencia e auditoria."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.obter_empresa import (
    ConfiguracaoEmpresa,
    autorizar_membro,
    configuracao_da_empresa,
)

CAMPOS_CONFIGURACAO = (
    "nome",
    "segmento",
    "descricao",
    "horario_atendimento",
    "endereco",
    "telefone",
    "site",
    "instrucoes_atendimento",
)


class ConflitoAtualizacaoEmpresa(Exception):
    """Indica que a versao enviada nao representa mais o estado atual."""


@dataclass(frozen=True)
class DadosAtualizacaoEmpresa:
    """Agrupa a substituicao integral recebida pela camada de dominio."""

    nome: str
    segmento: str
    descricao: str
    horario_atendimento: str
    endereco: str
    telefone: str
    site: str
    instrucoes_atendimento: str
    atualizado_em: datetime


def _snapshot(empresa: Empresa) -> dict[str, Any]:
    """Produz o estado restauravel sem metadados ou campos sensiveis."""
    return {campo: getattr(empresa, campo) for campo in CAMPOS_CONFIGURACAO}


def _versao_http(valor: datetime) -> datetime:
    """Reduz a versao a precisao de milissegundos publicada pela API."""
    return valor.replace(microsecond=(valor.microsecond // 1000) * 1000)


@transaction.atomic
def atualizar_empresa(
    *,
    empresa: Empresa,
    dados: DadosAtualizacaoEmpresa,
    ator: Usuario,
    correlacao: str,
) -> ConfiguracaoEmpresa:
    """Autoriza, valida a versao, persiste o diff e registra auditoria."""
    empresa_atual = Empresa.objects.select_for_update().get(pk=empresa.pk)
    membro = autorizar_membro(empresa=empresa_atual, ator=ator)
    if membro.papel != MembroEmpresa.Papel.ADMINISTRADOR:
        raise PermissionDenied
    if _versao_http(empresa_atual.atualizado_em) != _versao_http(dados.atualizado_em):
        raise ConflitoAtualizacaoEmpresa(
            "A empresa foi atualizada por outra pessoa. Recarregue os dados."
        )

    antes = _snapshot(empresa_atual)
    depois = {campo: getattr(dados, campo) for campo in CAMPOS_CONFIGURACAO}
    campos_alterados = [
        campo for campo in CAMPOS_CONFIGURACAO if antes[campo] != depois[campo]
    ]
    if not campos_alterados:
        return configuracao_da_empresa(empresa_atual)

    for campo in CAMPOS_CONFIGURACAO:
        setattr(empresa_atual, campo, depois[campo])
    empresa_atual.full_clean()
    empresa_atual.save(update_fields=[*campos_alterados, "atualizado_em"])

    registrar_alteracao(
        empresa=empresa_atual,
        objeto=empresa_atual,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        depois=depois,
        campos_alterados=campos_alterados,
        ator=ator,
        origem="api",
        correlacao=correlacao,
    )
    return configuracao_da_empresa(empresa_atual)
