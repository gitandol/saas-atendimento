"""Testes do middleware que anexa a empresa ativa a requisicao."""

import pytest
from django.test import RequestFactory

from apps.contas.models import Usuario
from apps.empresas.middleware.empresa_ativa import EmpresaAtivaMiddleware
from apps.empresas.models import Empresa, MembroEmpresa
from config.settings.base import MIDDLEWARE


@pytest.fixture
def requisicao(db):
    """Cria uma requisicao autenticada com uma empresa ativa selecionada."""
    usuario = Usuario.objects.create_user(
        email="middleware@example.com", password="senha"
    )
    empresa = Empresa.objects.create(nome="Empresa middleware")
    membro = MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ADMINISTRADOR,
    )
    requisicao = RequestFactory().get("/")
    requisicao.user = usuario
    requisicao.session = {"empresa_ativa_id": str(empresa.pk)}
    requisicao.empresa_esperada = empresa
    requisicao.membro_esperado = membro
    return requisicao


@pytest.mark.django_db
def test_middleware_anexa_empresa_e_membro_ativos(requisicao):
    """Disponibiliza a resolucao validada para as camadas posteriores."""
    middleware = EmpresaAtivaMiddleware(lambda request: request)

    resultado = middleware(requisicao)

    assert resultado.empresa_ativa == requisicao.empresa_esperada
    assert resultado.membro_empresa_ativo == requisicao.membro_esperado


def test_middleware_vem_apos_autenticacao():
    """Garante que request.user ja existe ao resolver a empresa ativa."""
    autenticacao = "django.contrib.auth.middleware.AuthenticationMiddleware"
    empresa_ativa = "apps.empresas.middleware.empresa_ativa.EmpresaAtivaMiddleware"

    assert MIDDLEWARE.index(empresa_ativa) == MIDDLEWARE.index(autenticacao) + 1
