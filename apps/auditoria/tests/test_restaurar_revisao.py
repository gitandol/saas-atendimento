"""Testes de imutabilidade e restauracao do historico."""

import pytest
from django.core.exceptions import ValidationError


def _registrar_empresa(empresa, ator, nome: str):
    """Cria uma revisao real da empresa para os cenarios de restauracao."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao

    return registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes={"nome": empresa.nome},
        depois={"nome": nome},
        campos_alterados=["nome"],
        ator=ator,
        origem="teste",
        correlacao=f"corr-{nome}",
    )


@pytest.mark.django_db
def test_evento_existente_nao_pode_ser_editado_ou_excluido() -> None:
    """Preserva a trilha mesmo por uso direto da camada de modelos."""
    from apps.contas.models import Usuario
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Imutavel")
    ator = Usuario.objects.create_user(email="imutavel@example.com")
    evento = _registrar_empresa(empresa, ator, "Registrado")

    evento.origem = "alterada"
    with pytest.raises(ValidationError):
        evento.save()
    with pytest.raises(ValidationError):
        evento.delete()


@pytest.mark.django_db
def test_restauracao_aplica_snapshot_e_cria_nova_revisao_restore() -> None:
    """Restaura estado anterior sem apagar nenhuma revisao existente."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.auditoria.services.restaurar_revisao import restaurar_revisao
    from apps.contas.models import Usuario
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Original")
    ator = Usuario.objects.create_user(email="restore@example.com")
    evento_original = _registrar_empresa(empresa, ator, "Original")
    empresa.nome = "Atual"
    empresa.save(update_fields=["nome"])
    _registrar_empresa(empresa, ator, "Atual")

    restaurado = restaurar_revisao(
        empresa=empresa,
        revisao=evento_original.revisao,
        ator=ator,
        origem="api",
        correlacao="corr-restore",
    )

    empresa.refresh_from_db()
    assert empresa.nome == "Original"
    assert RevisaoObjeto.objects.count() == 3
    assert restaurado.acao == EventoAuditoria.Acao.RESTAURACAO
    assert restaurado.revisao.numero == 3
    assert restaurado.depois == {"nome": "Original"}
