"""Consulta e altera a configuracao de IA com isolamento e auditoria."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.obter_empresa import autorizar_membro
from apps.ia.models import ConfiguracaoIA
from apps.ia.services.criptografia import criptografar_chave

CAMPOS_PUBLICOS = (
    "modelo",
    "nome_assistente",
    "personalidade",
    "mensagem_saudacao",
    "mensagem_falha",
    "respostas_automaticas_ativas",
)


class ConflitoAtualizacaoIA(Exception):
    """Indica tentativa de salvar uma versao obsoleta da configuracao."""


@dataclass(frozen=True)
class ConfiguracaoIAPublica:
    """Expoe ajustes de IA sem carregar a credencial persistida."""

    modelo: str
    nome_assistente: str
    personalidade: str
    mensagem_saudacao: str
    mensagem_falha: str
    respostas_automaticas_ativas: bool
    chave_configurada: bool
    atualizado_em: datetime | None


@dataclass(frozen=True)
class DadosConfiguracaoIA:
    """Agrupa os ajustes editaveis recebidos pela camada de dominio."""

    modelo: str
    nome_assistente: str
    personalidade: str
    mensagem_saudacao: str
    mensagem_falha: str
    respostas_automaticas_ativas: bool
    chave_api: str = ""
    atualizado_em: datetime | None = None


def _publicar(configuracao: ConfiguracaoIA | None) -> ConfiguracaoIAPublica:
    """Converte o estado persistido em uma representacao sem segredo."""
    if configuracao is None:
        return ConfiguracaoIAPublica(
            modelo="gpt-4.1-mini",
            nome_assistente="",
            personalidade="",
            mensagem_saudacao="",
            mensagem_falha="",
            respostas_automaticas_ativas=False,
            chave_configurada=False,
            atualizado_em=None,
        )
    return ConfiguracaoIAPublica(
        **{campo: getattr(configuracao, campo) for campo in CAMPOS_PUBLICOS},
        chave_configurada=bool(configuracao.chave_api_criptografada),
        atualizado_em=configuracao.atualizado_em,
    )


def _snapshot(configuracao: ConfiguracaoIA | None) -> dict[str, Any]:
    """Produz estado auditavel sem cifra ou credencial em texto puro."""
    return {
        campo: valor
        for campo, valor in _publicar(configuracao).__dict__.items()
        if campo != "atualizado_em"
    }


def _exigir_administrador(*, empresa: Empresa, ator: Usuario) -> None:
    """Exige papel administrativo ativo dentro da empresa informada."""
    membro = autorizar_membro(empresa=empresa, ator=ator)
    if membro.papel != MembroEmpresa.Papel.ADMINISTRADOR:
        raise PermissionDenied


def _versao_http(valor: datetime) -> datetime:
    """Compara a versao com a precisao de milissegundos publicada pela API."""
    return valor.replace(microsecond=(valor.microsecond // 1000) * 1000)


def obter_configuracao(*, empresa: Empresa, ator: Usuario) -> ConfiguracaoIAPublica:
    """Consulta somente a configuracao da empresa autorizada."""
    autorizar_membro(empresa=empresa, ator=ator)
    return _publicar(ConfiguracaoIA.objects.filter(empresa=empresa).first())


@transaction.atomic
def atualizar_configuracao(
    *, empresa: Empresa, ator: Usuario, dados: DadosConfiguracaoIA, correlacao: str
) -> ConfiguracaoIAPublica:
    """Persiste ajustes, preserva chave vazia e registra auditoria segura."""
    empresa = Empresa.objects.select_for_update().get(pk=empresa.pk)
    _exigir_administrador(empresa=empresa, ator=ator)
    configuracao = (
        ConfiguracaoIA.objects.select_for_update().filter(empresa=empresa).first()
    )
    criada = configuracao is None
    if configuracao is None:
        configuracao = ConfiguracaoIA(empresa=empresa)
    elif dados.atualizado_em is None or _versao_http(
        configuracao.atualizado_em
    ) != _versao_http(dados.atualizado_em):
        raise ConflitoAtualizacaoIA(
            "A configuracao foi atualizada por outra pessoa. Recarregue os dados."
        )

    antes = {} if criada else _snapshot(configuracao)
    for campo in CAMPOS_PUBLICOS:
        setattr(configuracao, campo, getattr(dados, campo))
    chave_alterada = bool(dados.chave_api.strip())
    if chave_alterada:
        configuracao.chave_api_criptografada = criptografar_chave(
            dados.chave_api.strip()
        )
    depois = _snapshot(configuracao)
    campos_alterados = [
        campo for campo, valor in depois.items() if antes.get(campo) != valor
    ]
    if chave_alterada and not criada:
        campos_alterados.append("chave_api")
    if not criada and not campos_alterados:
        return _publicar(configuracao)

    configuracao.full_clean()
    configuracao.save()
    registrar_alteracao(
        empresa=empresa,
        objeto=configuracao,
        acao=EventoAuditoria.Acao.CRIACAO
        if criada
        else EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        depois=depois,
        campos_alterados=campos_alterados,
        ator=ator,
        origem="api",
        correlacao=correlacao,
    )
    return _publicar(configuracao)


@transaction.atomic
def remover_chave(
    *, empresa: Empresa, ator: Usuario, correlacao: str
) -> ConfiguracaoIAPublica:
    """Remove explicitamente a credencial e audita apenas seu indicador."""
    empresa = Empresa.objects.select_for_update().get(pk=empresa.pk)
    _exigir_administrador(empresa=empresa, ator=ator)
    configuracao = (
        ConfiguracaoIA.objects.select_for_update().filter(empresa=empresa).first()
    )
    if configuracao is None or not configuracao.chave_api_criptografada:
        return _publicar(configuracao)
    antes = _snapshot(configuracao)
    configuracao.chave_api_criptografada = ""
    configuracao.save(update_fields=["chave_api_criptografada", "atualizado_em"])
    depois = _snapshot(configuracao)
    registrar_alteracao(
        empresa=empresa,
        objeto=configuracao,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        depois=depois,
        campos_alterados=["chave_configurada"],
        ator=ator,
        origem="api",
        correlacao=correlacao,
    )
    return _publicar(configuracao)
