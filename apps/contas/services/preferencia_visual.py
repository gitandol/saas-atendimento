"""Consulta e atualiza preferencias visuais com isolamento e auditoria."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import PreferenciaVisual, Usuario
from apps.empresas.models import Empresa, MembroEmpresa


@dataclass(frozen=True)
class DadosPreferenciaVisual:
    """Representa a preferencia consumida fora da persistencia."""

    tema: str
    modo: str


def _validar_associacao(
    empresa: Empresa,
    usuario: Usuario,
    *,
    bloquear: bool = False,
) -> None:
    """Recusa operacoes fora de uma associacao ativa."""
    associacoes = MembroEmpresa.objects
    if bloquear:
        associacoes = associacoes.select_for_update()
    associacao_existe = associacoes.filter(
        empresa=empresa,
        usuario=usuario,
        ativo=True,
    ).exists()
    if not associacao_existe:
        raise PermissionDenied


def obter_preferencia_visual(
    *,
    empresa: Empresa,
    usuario: Usuario,
) -> DadosPreferenciaVisual:
    """Retorna a preferencia persistida ou os valores iniciais seguros."""
    _validar_associacao(empresa, usuario)
    preferencia = PreferenciaVisual.objects.filter(
        empresa=empresa,
        usuario=usuario,
    ).first()
    if preferencia is None:
        return DadosPreferenciaVisual(
            tema=PreferenciaVisual.Tema.AZUL,
            modo=PreferenciaVisual.Modo.SISTEMA,
        )
    return DadosPreferenciaVisual(tema=preferencia.tema, modo=preferencia.modo)


@transaction.atomic
def atualizar_preferencia_visual(
    *,
    empresa: Empresa,
    usuario: Usuario,
    tema: str,
    modo: str,
    origem: str,
    correlacao: str,
) -> PreferenciaVisual:
    """Persiste uma preferencia valida no escopo e registra sua revisao."""
    _validar_associacao(empresa, usuario, bloquear=True)
    preferencia = (
        PreferenciaVisual.objects.select_for_update()
        .filter(empresa=empresa, usuario=usuario)
        .first()
    )
    antes = (
        {"tema": preferencia.tema, "modo": preferencia.modo}
        if preferencia is not None
        else {}
    )
    if preferencia is None:
        preferencia = PreferenciaVisual(empresa=empresa, usuario=usuario)

    preferencia.tema = tema
    preferencia.modo = modo
    preferencia.full_clean()
    preferencia.save()

    depois = {"tema": preferencia.tema, "modo": preferencia.modo}
    campos_alterados = [
        campo for campo in ("tema", "modo") if antes.get(campo) != depois[campo]
    ]
    if campos_alterados:
        registrar_alteracao(
            empresa=empresa,
            objeto=preferencia,
            acao=(
                EventoAuditoria.Acao.ATUALIZACAO
                if antes
                else EventoAuditoria.Acao.CRIACAO
            ),
            antes=antes,
            depois=depois,
            campos_alterados=campos_alterados,
            ator=usuario,
            origem=origem,
            correlacao=correlacao,
        )
    return preferencia
