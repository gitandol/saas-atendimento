"""Testes da resolucao segura da empresa ativa da requisicao."""

from datetime import datetime, timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    PermissaoEmpresaNegada,
    exigir_administrador,
    exigir_empresa_ativa,
    obter_empresa_ativa,
    obter_membro_ativo,
)


@pytest.fixture
def requisicao_factory():
    """Fornece requisicoes autenticadas com uma sessao mutavel."""

    def criar(usuario, sessao=None):
        """Monta uma requisicao autenticada com a sessao informada."""
        requisicao = RequestFactory().get("/")
        requisicao.user = usuario
        requisicao.session = sessao if sessao is not None else {}
        return requisicao

    return criar


@pytest.fixture
def usuario(db):
    """Cria um usuario para os testes de empresa ativa."""
    return Usuario.objects.create_user(email="usuario@example.com", password="senha")


def criar_membro(usuario, empresa, papel, ativo=True):
    """Vincula um usuario a uma empresa para o cenario testado."""
    return MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=papel,
        ativo=ativo,
    )


@pytest.mark.django_db
def test_membro_inativo_nao_pode_selecionar_empresa(requisicao_factory, usuario):
    """Descarta uma selecao de sessao cuja associacao foi desativada."""
    empresa = Empresa.objects.create(nome="Empresa inativa")
    criar_membro(usuario, empresa, MembroEmpresa.Papel.ADMINISTRADOR, ativo=False)
    requisicao = requisicao_factory(usuario, {"empresa_ativa_id": str(empresa.pk)})

    assert obter_membro_ativo(requisicao) is None
    assert "empresa_ativa_id" not in requisicao.session


@pytest.mark.django_db
def test_uuid_invalido_na_sessao_e_substituido_por_fallback_ativo(
    requisicao_factory, usuario
):
    """Nunca usa um UUID invalido para autorizar uma empresa."""
    empresa = Empresa.objects.create(nome="Empresa ativa")
    criar_membro(usuario, empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    requisicao = requisicao_factory(usuario, {"empresa_ativa_id": "nao-e-um-uuid"})

    assert obter_empresa_ativa(requisicao) == empresa
    assert requisicao.session["empresa_ativa_id"] == str(empresa.pk)


@pytest.mark.django_db
def test_fallback_escolhe_a_associacao_ativa_mais_antiga(requisicao_factory, usuario):
    """Resolve a primeira empresa ativa em ordem deterministica."""
    empresa_recente = Empresa.objects.create(nome="Empresa recente")
    empresa_antiga = Empresa.objects.create(nome="Empresa antiga")
    membro_recente = criar_membro(
        usuario, empresa_recente, MembroEmpresa.Papel.ATENDENTE
    )
    membro_antigo = criar_membro(usuario, empresa_antiga, MembroEmpresa.Papel.ATENDENTE)
    agora = timezone.make_aware(datetime(2026, 8, 22, 12, 0))
    MembroEmpresa.objects.filter(pk=membro_recente.pk).update(criado_em=agora)
    MembroEmpresa.objects.filter(pk=membro_antigo.pk).update(
        criado_em=agora - timedelta(days=1)
    )
    requisicao = requisicao_factory(usuario)

    assert obter_membro_ativo(requisicao).pk == membro_antigo.pk
    assert requisicao.session["empresa_ativa_id"] == str(empresa_antiga.pk)


@pytest.mark.django_db
def test_exigir_empresa_ativa_sinaliza_ausencia(requisicao_factory, usuario):
    """Interrompe fluxos sem associacao ativa valida."""
    requisicao = requisicao_factory(usuario)

    with pytest.raises(EmpresaAtivaAusente):
        exigir_empresa_ativa(requisicao)


@pytest.mark.django_db
def test_administrador_e_aceito(requisicao_factory, usuario):
    """Permite operacoes administrativas ao membro administrador ativo."""
    empresa = Empresa.objects.create(nome="Empresa administrada")
    membro = criar_membro(usuario, empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    requisicao = requisicao_factory(usuario, {"empresa_ativa_id": str(empresa.pk)})

    assert exigir_administrador(requisicao) == membro


@pytest.mark.django_db
def test_atendente_e_rejeitado_em_operacao_administrativa(requisicao_factory, usuario):
    """Nao confunde o papel de atendente com o de administrador."""
    empresa = Empresa.objects.create(nome="Empresa atendida")
    criar_membro(usuario, empresa, MembroEmpresa.Papel.ATENDENTE)
    requisicao = requisicao_factory(usuario, {"empresa_ativa_id": str(empresa.pk)})

    with pytest.raises(PermissaoEmpresaNegada):
        exigir_administrador(requisicao)
