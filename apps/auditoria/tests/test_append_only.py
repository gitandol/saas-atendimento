"""Testes da protecao append-only de eventos e revisoes."""

import pytest
from django.core.exceptions import ValidationError


def _evento_e_revisao():
    """Cria um par persistido pela unica interface legitima de escrita."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Append only")
    evento = registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        depois={"nome": empresa.nome},
        campos_alterados=["nome"],
        ator=None,
        origem="teste",
        correlacao="corr-append-only",
    )
    return evento, evento.revisao


@pytest.mark.django_db
def test_base_manager_do_evento_tambem_recusa_mutacao() -> None:
    """Impede que a manager-base contorne a protecao da manager publica."""
    from apps.auditoria.models import EventoAuditoria

    evento, _revisao = _evento_e_revisao()

    with pytest.raises(ValidationError):
        EventoAuditoria._base_manager.filter(pk=evento.pk).update(origem="alterada")
    with pytest.raises(ValidationError):
        EventoAuditoria._base_manager.filter(pk=evento.pk).delete()


@pytest.mark.django_db
def test_revisao_recusa_mutacao_por_instancia_e_queryset() -> None:
    """Preserva numero e snapshot usados como fonte de restauracao."""
    from apps.auditoria.models import RevisaoObjeto

    _evento, revisao = _evento_e_revisao()
    revisao.snapshot = {"nome": "Adulterado"}

    with pytest.raises(ValidationError):
        revisao.save()
    with pytest.raises(ValidationError):
        revisao.delete()
    with pytest.raises(ValidationError):
        RevisaoObjeto._base_manager.filter(pk=revisao.pk).update(numero=99)
    with pytest.raises(ValidationError):
        RevisaoObjeto._base_manager.filter(pk=revisao.pk).delete()
