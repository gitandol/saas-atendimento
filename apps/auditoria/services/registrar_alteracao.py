"""Registra eventos e revisoes de forma atomica e explicita."""

from collections.abc import Mapping, Sequence
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction

from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
from apps.auditoria.services.sanitizar_snapshot import (
    proteger_snapshot_restauravel,
    sanitizar_snapshot,
)
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


def _validar_objeto_da_empresa(empresa: Empresa, objeto: models.Model) -> None:
    """Recusa objetos globais ou vinculados a outro tenant."""
    if isinstance(objeto, Empresa):
        pertence = objeto.pk == empresa.pk
    else:
        pertence = getattr(objeto, "empresa_id", None) == empresa.pk
    if not pertence:
        raise ObjectDoesNotExist


@transaction.atomic
def registrar_alteracao(
    *,
    empresa: Empresa,
    objeto: models.Model,
    acao: str,
    antes: Mapping[str, Any],
    depois: Mapping[str, Any],
    campos_alterados: Sequence[str],
    ator: Usuario | None,
    origem: str,
    correlacao: str,
    justificativa: str = "",
) -> EventoAuditoria:
    """Cria o proximo snapshot e seu evento na mesma transacao."""
    type(empresa).objects.select_for_update().get(pk=empresa.pk)
    _validar_objeto_da_empresa(empresa, objeto)
    tipo_objeto = objeto._meta.label_lower
    objeto_id = str(objeto.pk)
    ultima = (
        RevisaoObjeto.objects.filter(
            empresa=empresa,
            tipo_objeto=tipo_objeto,
            objeto_id=objeto_id,
        )
        .order_by("-numero")
        .first()
    )
    revisao = RevisaoObjeto.objects.create(
        empresa=empresa,
        tipo_objeto=tipo_objeto,
        objeto_id=objeto_id,
        numero=(ultima.numero + 1) if ultima else 1,
        snapshot=proteger_snapshot_restauravel(dict(depois)),
    )
    return EventoAuditoria.objects.create(
        empresa=empresa,
        revisao=revisao,
        tipo_objeto=tipo_objeto,
        objeto_id=objeto_id,
        acao=acao,
        antes=sanitizar_snapshot(dict(antes)),
        depois=sanitizar_snapshot(dict(depois)),
        campos_alterados=list(campos_alterados),
        ator=ator,
        origem=origem,
        justificativa=justificativa.strip(),
        correlacao=correlacao,
    )
