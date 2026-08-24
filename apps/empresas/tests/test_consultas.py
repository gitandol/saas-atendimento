"""Testes das consultas de empresas permitidas ao usuario."""

import pytest

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.consultas import (
    listar_empresas_permitidas,
    obter_empresa_permitida,
)


@pytest.fixture
def empresa_a(db):
    """Cria a primeira empresa e seu administrador."""
    empresa = Empresa.objects.create(nome="Empresa A")
    empresa.usuario_administrador = Usuario.objects.create_user(
        email="administrador-a@example.com",
        password="senha",
    )
    MembroEmpresa.objects.create(
        usuario=empresa.usuario_administrador,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ADMINISTRADOR,
    )
    return empresa


@pytest.fixture
def empresa_b(db):
    """Cria uma empresa de outro tenant e seu administrador."""
    empresa = Empresa.objects.create(nome="Empresa original B")
    usuario = Usuario.objects.create_user(
        email="administrador-b@example.com",
        password="senha",
    )
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ADMINISTRADOR,
    )
    return empresa


@pytest.mark.django_db
def test_consulta_nao_retorna_registros_de_outra_empresa(empresa_a, empresa_b):
    """Lista somente as empresas vinculadas ativamente ao usuario."""
    Empresa.objects.filter(pk=empresa_b.pk).update(nome="Empresa B")

    resultado = listar_empresas_permitidas(empresa_a.usuario_administrador)

    assert list(resultado) == [empresa_a]


@pytest.mark.django_db
def test_listagem_ignora_associacao_inativa(empresa_a):
    """Nao expoe empresas cuja associacao foi desativada."""
    MembroEmpresa.objects.filter(
        usuario=empresa_a.usuario_administrador,
        empresa=empresa_a,
    ).update(ativo=False)

    resultado = listar_empresas_permitidas(empresa_a.usuario_administrador)

    assert list(resultado) == []


@pytest.mark.django_db
def test_obter_empresa_permitida_rejeita_empresa_de_outro_usuario(empresa_a, empresa_b):
    """Nao recupera empresa sem associacao ativa do usuario solicitante."""
    with pytest.raises(Empresa.DoesNotExist):
        obter_empresa_permitida(empresa_a.usuario_administrador, empresa_b.pk)
