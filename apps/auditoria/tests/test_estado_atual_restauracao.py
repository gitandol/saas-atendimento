"""Testa a fotografia real anterior a uma restauracao."""

import pytest


@pytest.mark.django_db
def test_restore_registra_antes_a_partir_do_objeto_bloqueado() -> None:
    """Evita declarar como anterior um snapshot historico ja desatualizado."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.auditoria.services.restaurar_revisao import restaurar_revisao
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Original")
    original = registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes={},
        depois={"nome": "Original"},
        campos_alterados=["nome"],
        ator=None,
        origem="teste",
        correlacao="corr-original",
    )
    empresa.nome = "Deriva sem evento"
    empresa.save(update_fields=["nome"])

    restaurado = restaurar_revisao(
        empresa=empresa,
        revisao=original.revisao,
        ator=None,
        origem="teste",
        correlacao="corr-restaura-deriva",
    )

    assert restaurado.antes == {"nome": "Deriva sem evento"}
