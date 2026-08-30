"""Restaura snapshots sob as invariantes atuais do modelo."""

import json
from typing import Any

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction

from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.auditoria.services.sanitizar_snapshot import (
    VALOR_PROTEGIDO,
    restaurar_snapshot_protegido,
)
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


class RevisaoNaoRestauravel(Exception):
    """Indica conflito entre um snapshot historico e as invariantes atuais."""


def _contem_valor_protegido(valor: Any) -> bool:
    """Detecta marcadores que jamais podem ser reaplicados como segredo real."""
    if valor == VALOR_PROTEGIDO:
        return True
    if isinstance(valor, dict):
        return any(_contem_valor_protegido(item) for item in valor.values())
    if isinstance(valor, list):
        return any(_contem_valor_protegido(item) for item in valor)
    return False


def _valor_json(valor: Any) -> Any:
    """Converte valores de campos Django para tipos aceitos por JSONField."""
    return json.loads(json.dumps(valor, cls=DjangoJSONEncoder))


def _objeto_da_revisao(empresa: Empresa, revisao: RevisaoObjeto) -> models.Model:
    """Resolve e bloqueia o objeto somente quando pertence a empresa informada."""
    modelo = apps.get_model(revisao.tipo_objeto)
    objeto = modelo.objects.select_for_update().get(pk=revisao.objeto_id)
    empresa_id = (
        objeto.pk
        if isinstance(objeto, Empresa)
        else getattr(objeto, "empresa_id", None)
    )
    if empresa_id != empresa.pk:
        raise ObjectDoesNotExist
    return objeto


@transaction.atomic
def restaurar_revisao(
    *,
    empresa: Empresa,
    revisao: RevisaoObjeto,
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> EventoAuditoria:
    """Aplica campos restauraveis, valida o modelo e registra um novo evento."""
    empresa = type(empresa).objects.select_for_update().get(pk=empresa.pk)
    revisao = RevisaoObjeto.objects.select_for_update().get(
        pk=revisao.pk,
        empresa=empresa,
    )
    snapshot = restaurar_snapshot_protegido(revisao.snapshot)
    if _contem_valor_protegido(snapshot):
        raise RevisaoNaoRestauravel("O snapshot contem valores protegidos.")

    objeto = _objeto_da_revisao(empresa, revisao)
    campos = {}
    for campo in objeto._meta.concrete_fields:
        if (
            not campo.editable
            or campo.primary_key
            or campo.auto_created
            or campo.name == "empresa"
        ):
            continue
        campos[campo.name] = campo
        if campo.is_relation:
            campos[campo.attname] = campo
    aplicaveis = [nome for nome in snapshot if nome in campos]
    if not aplicaveis:
        raise RevisaoNaoRestauravel("O snapshot nao possui campos restauraveis.")

    antes = {
        nome: _valor_json(campos[nome].value_from_object(objeto)) for nome in aplicaveis
    }
    depois = {nome: snapshot[nome] for nome in aplicaveis}
    conversa = objeto._meta.label_lower == "atendimento.conversa"
    if conversa:
        versao_atual = objeto.versao
        if "versao" not in aplicaveis:
            aplicaveis.append("versao")
        antes["versao"] = versao_atual
        depois["versao"] = versao_atual + 1
    for nome, valor in depois.items():
        campo = campos[nome]
        atributo = campo.attname if campo.is_relation else campo.name
        setattr(objeto, atributo, valor)
    if conversa and (
        (objeto.modo == "IA" and objeto.atendente_id is not None)
        or (objeto.modo == "HUMANO" and objeto.atendente_id is None)
    ):
        raise RevisaoNaoRestauravel(
            "O snapshot viola a responsabilidade atual da conversa."
        )
    try:
        objeto.full_clean()
    except ValidationError as erro:
        raise RevisaoNaoRestauravel("O snapshot viola as regras atuais.") from erro
    objeto.save(update_fields={campos[nome].name for nome in aplicaveis})
    if not isinstance(objeto, Empresa) and objeto.empresa_id != empresa.pk:
        raise ObjectDoesNotExist
    return registrar_alteracao(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.RESTAURACAO,
        antes=antes,
        depois=depois,
        campos_alterados=aplicaveis,
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
