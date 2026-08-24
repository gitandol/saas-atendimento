"""Testes negativos de isolamento, imutabilidade e restauracao."""

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError


@pytest.mark.django_db
def test_registro_recusa_objeto_de_outra_empresa() -> None:
    """Impede atribuir um objeto externo ao historico da empresa ativa."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.contas.models import Usuario
    from apps.empresas.models import Empresa, MembroEmpresa

    permitida = Empresa.objects.create(nome="Permitida")
    externa = Empresa.objects.create(nome="Externa")
    usuario = Usuario.objects.create_user(email="cross-tenant@example.com")
    membro_externo = MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=externa,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )

    with pytest.raises(ObjectDoesNotExist):
        registrar_alteracao(
            empresa=permitida,
            objeto=membro_externo,
            acao=EventoAuditoria.Acao.ATUALIZACAO,
            antes={},
            depois={"papel": MembroEmpresa.Papel.ATENDENTE},
            campos_alterados=["papel"],
            ator=None,
            origem="teste",
            correlacao="corr-cross-tenant",
        )


@pytest.mark.django_db
def test_evento_recusa_update_e_delete_em_massa() -> None:
    """Fecha os atalhos comuns da ORM que burlariam save e delete da instancia."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Imutavel em massa")
    evento = registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        depois={"nome": empresa.nome},
        campos_alterados=["nome"],
        ator=None,
        origem="teste",
        correlacao="corr-imutavel-massa",
    )

    with pytest.raises(ValidationError):
        EventoAuditoria.objects.filter(pk=evento.pk).update(origem="alterada")
    with pytest.raises(ValidationError):
        EventoAuditoria.objects.filter(pk=evento.pk).delete()


@pytest.mark.django_db
def test_restauracao_ignora_empresa_do_snapshot_e_preserva_tenant() -> None:
    """Nunca permite que um snapshot mova um objeto entre empresas."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.auditoria.services.restaurar_revisao import restaurar_revisao
    from apps.contas.models import Usuario
    from apps.empresas.models import Empresa, MembroEmpresa

    permitida = Empresa.objects.create(nome="Permitida")
    externa = Empresa.objects.create(nome="Externa")
    usuario = Usuario.objects.create_user(email="tenant-restore@example.com")
    membro = MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=permitida,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    evento = registrar_alteracao(
        empresa=permitida,
        objeto=membro,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes={"papel": MembroEmpresa.Papel.ATENDENTE},
        depois={
            "empresa": str(externa.pk),
            "papel": MembroEmpresa.Papel.ADMINISTRADOR,
        },
        campos_alterados=["empresa", "papel"],
        ator=usuario,
        origem="teste",
        correlacao="corr-tenant-snapshot",
    )

    restaurar_revisao(
        empresa=permitida,
        revisao=evento.revisao,
        ator=usuario,
        origem="teste",
        correlacao="corr-tenant-restore",
    )

    membro.refresh_from_db()
    assert membro.empresa == permitida
    assert membro.papel == MembroEmpresa.Papel.ADMINISTRADOR
