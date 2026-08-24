"""Testes do service de preferencia visual por usuario e empresa."""

from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import PreferenciaVisual, Usuario
from apps.contas.services.preferencia_visual import atualizar_preferencia_visual
from apps.empresas.models import Empresa, MembroEmpresa


def _associar(usuario: Usuario, empresa: Empresa) -> None:
    """Associa um usuario ao tenant usado pelo service real."""
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )


@pytest.mark.django_db
def test_atualiza_preferencia_e_registra_auditoria() -> None:
    """Persiste tema e modo no tenant e registra a alteracao rastreavel."""
    empresa = Empresa.objects.create(nome="Empresa Visual")
    usuario = Usuario.objects.create_user(email="visual@example.com", password="senha")
    _associar(usuario, empresa)

    preferencia = atualizar_preferencia_visual(
        empresa=empresa,
        usuario=usuario,
        tema="violeta",
        modo="ESCURO",
        origem="api",
        correlacao="corr-visual",
    )

    assert preferencia.tema == "violeta"
    assert preferencia.modo == "ESCURO"
    evento = EventoAuditoria.objects.get(
        tipo_objeto="contas.preferenciavisual",
        objeto_id=str(preferencia.pk),
    )
    assert evento.empresa == empresa
    assert evento.ator == usuario
    assert evento.campos_alterados == ["tema", "modo"]
    assert evento.depois == {"tema": "violeta", "modo": "ESCURO"}


@pytest.mark.django_db
def test_usuario_nao_altera_preferencia_de_empresa_sem_associacao() -> None:
    """Recusa tenant externo sem modificar a preferencia nele existente."""
    permitida = Empresa.objects.create(nome="Permitida")
    externa = Empresa.objects.create(nome="Externa")
    usuario = Usuario.objects.create_user(email="isolado@example.com", password="senha")
    outro = Usuario.objects.create_user(email="outro@example.com", password="senha")
    _associar(usuario, permitida)
    _associar(outro, externa)
    existente = PreferenciaVisual.objects.create(
        empresa=externa,
        usuario=outro,
        tema="azul",
        modo="CLARO",
    )

    with pytest.raises(PermissionDenied):
        atualizar_preferencia_visual(
            empresa=externa,
            usuario=usuario,
            tema="rubi",
            modo="ESCURO",
            origem="api",
            correlacao=str(uuid4()),
        )

    existente.refresh_from_db()
    assert (existente.tema, existente.modo) == ("azul", "CLARO")
