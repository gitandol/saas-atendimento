"""Testes do registro atomico de eventos e revisoes."""

from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_registra_evento_e_revisao_sequencial_com_metadados() -> None:
    """Captura mudanca rastreavel e protege seus snapshots na mesma operacao."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.contas.models import Usuario
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Antes")
    ator = Usuario.objects.create_user(email="ator@example.com", password="senha")

    primeiro = registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes={"nome": "Antes", "token": "antigo"},
        depois={"nome": "Depois", "token": "novo"},
        campos_alterados=["nome", "token"],
        ator=ator,
        origem="api",
        correlacao="corr-001",
    )
    segundo = registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes={"nome": "Depois"},
        depois={"nome": "Final"},
        campos_alterados=["nome"],
        ator=ator,
        origem="api",
        correlacao="corr-002",
    )

    assert [primeiro.revisao.numero, segundo.revisao.numero] == [1, 2]
    assert RevisaoObjeto.objects.count() == 2
    assert primeiro.antes["token"] == "[PROTEGIDO]"
    assert primeiro.depois["token"] == "[PROTEGIDO]"
    assert primeiro.campos_alterados == ["nome", "token"]
    assert primeiro.ator == ator
    assert primeiro.origem == "api"
    assert primeiro.correlacao == "corr-001"
    assert primeiro.tipo_objeto == "empresas.empresa"
    assert primeiro.objeto_id == str(empresa.pk)


@pytest.mark.django_db(transaction=True)
def test_falha_do_evento_desfaz_a_revisao() -> None:
    """Evita revisao orfa quando a gravacao do evento falha."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Atomica")

    with (
        patch.object(
            EventoAuditoria.objects,
            "create",
            side_effect=RuntimeError("falha controlada"),
        ),
        pytest.raises(RuntimeError, match="falha controlada"),
    ):
        registrar_alteracao(
            empresa=empresa,
            objeto=empresa,
            acao=EventoAuditoria.Acao.CRIACAO,
            antes={},
            depois={"nome": "Atomica"},
            campos_alterados=["nome"],
            ator=None,
            origem="teste",
            correlacao="corr-rollback",
        )

    assert RevisaoObjeto.objects.count() == 0
