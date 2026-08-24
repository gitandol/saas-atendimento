"""Testes do servico que expoe o perfil da empresa ativa."""

from uuid import uuid4

import pytest
from django.test import RequestFactory

from apps.contas.models import Usuario
from apps.contas.services.obter_perfil import obter_perfil
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.empresa_ativa import EmpresaAtivaAusente


def requisicao(usuario, empresa_id=None):
    """Monta requisicao autenticada com empresa selecionada."""
    resultado = RequestFactory().get("/")
    resultado.user = usuario
    resultado.session = {}
    if empresa_id:
        resultado.session["empresa_ativa_id"] = str(empresa_id)
    return resultado


def membro(usuario, empresa, papel):
    """Cria membro ativo na empresa."""
    return MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)


@pytest.mark.django_db
def test_perfil_do_administrador_reflete_empresa_ativa():
    """Informa privilegio do administrador ativo."""
    usuario = Usuario.objects.create_user(
        email="admin@example.com", password="senha", first_name="Ada"
    )
    empresa = Empresa.objects.create(nome="Administrada")
    membro(usuario, empresa, MembroEmpresa.Papel.ADMINISTRADOR)

    perfil = obter_perfil(requisicao(usuario, empresa.pk))

    assert perfil.email == usuario.email
    assert perfil.nome == "Ada"
    assert perfil.empresa_id == empresa.pk
    assert perfil.empresa_nome == empresa.nome
    assert perfil.papel == MembroEmpresa.Papel.ADMINISTRADOR
    assert perfil.pode_administrar is True


@pytest.mark.django_db
def test_perfil_do_atendente_nao_concede_administracao():
    """Distingue atendente de administrador."""
    usuario = Usuario.objects.create_user(
        email="atendente@example.com", password="senha"
    )
    empresa = Empresa.objects.create(nome="Atendida")
    membro(usuario, empresa, MembroEmpresa.Papel.ATENDENTE)

    perfil = obter_perfil(requisicao(usuario, empresa.pk))

    assert perfil.papel == MembroEmpresa.Papel.ATENDENTE
    assert perfil.pode_administrar is False


@pytest.mark.django_db
def test_perfil_aceita_uuid_de_empresa_permitida():
    """Usa explicitamente uma segunda empresa ativa permitida."""
    usuario = Usuario.objects.create_user(email="duas@example.com", password="senha")
    primeira = Empresa.objects.create(nome="Primeira")
    segunda = Empresa.objects.create(nome="Segunda")
    membro(usuario, primeira, MembroEmpresa.Papel.ATENDENTE)
    membro(usuario, segunda, MembroEmpresa.Papel.ADMINISTRADOR)

    perfil = obter_perfil(requisicao(usuario, primeira.pk), segunda.pk)

    assert perfil.empresa_id == segunda.pk
    assert perfil.pode_administrar is True


@pytest.mark.django_db
def test_perfil_com_uuid_sem_associacao_ativa_rejeita_usuario() -> None:
    """Exige alguma associacao ativa antes de consultar o UUID explicito."""
    usuario = Usuario.objects.create_user(
        email="sem-associacao@example.com", password="senha"
    )

    with pytest.raises(EmpresaAtivaAusente):
        obter_perfil(requisicao(usuario), uuid4())


@pytest.mark.django_db
def test_perfil_rejeita_uuid_de_empresa_de_outro_usuario():
    """Nao permite usar UUID externo ao usuario autenticado."""
    usuario = Usuario.objects.create_user(email="perfil@example.com", password="senha")
    permitida = Empresa.objects.create(nome="Permitida")
    externa = Empresa.objects.create(nome="Externa")
    membro(usuario, permitida, MembroEmpresa.Papel.ATENDENTE)

    with pytest.raises(Empresa.DoesNotExist):
        obter_perfil(requisicao(usuario, permitida.pk), externa.pk)
