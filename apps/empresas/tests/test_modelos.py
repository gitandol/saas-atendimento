"""Testes dos modelos que vinculam usuarios a empresas."""

import pytest
from django.db import IntegrityError

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


@pytest.fixture
def usuario(db):
    """Cria um usuario para associacao com uma empresa."""
    return Usuario.objects.create_user(email="membro@example.com", password="senha")


@pytest.fixture
def empresa(db):
    """Cria uma empresa para associacao com um usuario."""
    return Empresa.objects.create(nome="Empresa de teste")


@pytest.mark.django_db
def test_empresa_tem_uuid_e_registra_data_de_criacao(empresa):
    """Registra automaticamente o momento de criacao da empresa."""
    assert empresa.criado_em is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "papel",
    [MembroEmpresa.Papel.ADMINISTRADOR, MembroEmpresa.Papel.ATENDENTE],
)
def test_associacao_aceita_os_papeis_previstos(usuario, empresa, papel):
    """Persiste os dois papeis de acesso definidos para uma empresa."""
    membro = MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)

    assert membro.papel == papel


@pytest.mark.django_db
def test_associacao_e_unica_por_usuario_e_empresa(usuario, empresa):
    """Impede que um usuario tenha duas associacoes com a mesma empresa."""
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )

    with pytest.raises(IntegrityError):
        MembroEmpresa.objects.create(
            usuario=usuario,
            empresa=empresa,
            papel=MembroEmpresa.Papel.ADMINISTRADOR,
        )
