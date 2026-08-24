"""Testes HTTP da API de perfil."""

from unittest.mock import patch

import pytest
from django.test import Client

from apps.contas.models import Usuario
from apps.contas.services.obter_perfil import PerfilUsuario
from apps.empresas.models import Empresa, MembroEmpresa


def _criar_membro(
    email: str, empresa: Empresa, papel: str = MembroEmpresa.Papel.ATENDENTE
) -> Usuario:
    """Cria usuario autenticavel associado a uma empresa."""
    usuario = Usuario.objects.create_user(email=email, password="senha")
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    return usuario


@pytest.mark.django_db
def test_perfil_exige_sessao_autenticada() -> None:
    """Recusa leitura de perfil por usuario anonimo."""
    resposta = Client().get("/api/v1/perfil")

    assert resposta.status_code == 401


@pytest.mark.django_db
def test_perfil_da_empresa_ativa_retorna_contrato_completo() -> None:
    """Serializa dados do service para o membro autenticado."""
    empresa = Empresa.objects.create(nome="Empresa Perfil")
    usuario = _criar_membro(
        "perfil@example.com", empresa, MembroEmpresa.Papel.ADMINISTRADOR
    )
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/api/v1/perfil")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "email": "perfil@example.com",
        "nome": "",
        "empresa_id": str(empresa.pk),
        "empresa_nome": "Empresa Perfil",
        "papel": "ADMINISTRADOR",
        "pode_administrar": True,
    }


@pytest.mark.django_db
def test_perfil_delega_uuid_explicito_ao_service() -> None:
    """Converte UUID da rota e delega a autorizacao ao service."""
    empresa = Empresa.objects.create(nome="Empresa Delegada")
    usuario = _criar_membro("delegar@example.com", empresa)
    cliente = Client()
    cliente.force_login(usuario)
    perfil = PerfilUsuario(
        email=usuario.email,
        nome="Pessoa",
        empresa_id=empresa.pk,
        empresa_nome=empresa.nome,
        papel="ATENDENTE",
        pode_administrar=False,
    )

    with patch(
        "apps.contas.api.endpoints.perfil.obter_perfil", return_value=perfil
    ) as obter:
        resposta = cliente.get(f"/api/v1/perfil/{empresa.pk}")

    assert resposta.status_code == 200
    assert resposta.json()["empresa_id"] == str(empresa.pk)
    requisicao, empresa_id = obter.call_args.args
    assert requisicao.user == usuario
    assert empresa_id == empresa.pk


@pytest.mark.django_db
def test_perfil_sem_empresa_ativa_retorna_403() -> None:
    """Traduz ausencia de associacao ativa sem expor detalhes internos."""
    usuario = Usuario.objects.create_user(
        email="sem-perfil@example.com", password="senha"
    )
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get("/api/v1/perfil")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_ativa_ausente"


@pytest.mark.django_db
def test_perfil_com_uuid_sem_empresa_ativa_retorna_403() -> None:
    """Prioriza ausencia de associacao ativa antes do UUID solicitado."""
    empresa = Empresa.objects.create(nome="Nao associada")
    usuario = Usuario.objects.create_user(
        email="sem-empresa-uuid@example.com", password="senha"
    )
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get(f"/api/v1/perfil/{empresa.pk}")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_ativa_ausente"


@pytest.mark.django_db
def test_perfil_de_empresa_externa_retorna_404() -> None:
    """Oculta UUID de empresa a que o usuario nao pertence."""
    permitida = Empresa.objects.create(nome="Permitida")
    externa = Empresa.objects.create(nome="Externa")
    usuario = _criar_membro("isolado@example.com", permitida)
    cliente = Client()
    cliente.force_login(usuario)

    resposta = cliente.get(f"/api/v1/perfil/{externa.pk}")

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "perfil_nao_encontrado"
