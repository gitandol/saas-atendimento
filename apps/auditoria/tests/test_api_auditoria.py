"""Testes HTTP do historico e da restauracao."""

import pytest
from django.test import Client


def _membro(empresa, email: str, papel: str):
    """Cria um usuario membro para exercitar autorizacao real."""
    from apps.contas.models import Usuario
    from apps.empresas.models import MembroEmpresa

    usuario = Usuario.objects.create_user(email=email, password="senha")
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    return usuario


def _evento(empresa, ator, depois: dict, correlacao: str = "corr-api"):
    """Registra um evento real usado pelas consultas HTTP."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao

    return registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes={"nome": empresa.nome},
        depois=depois,
        campos_alterados=list(depois),
        ator=ator,
        origem="teste",
        correlacao=correlacao,
    )


@pytest.mark.django_db
def test_historico_exige_administrador_e_oculta_snapshots() -> None:
    """Recusa atendente e entrega metadados paginados sem estados internos."""
    from apps.empresas.models import Empresa, MembroEmpresa

    empresa = Empresa.objects.create(nome="Auditada")
    admin = _membro(
        empresa, "admin-auditoria@example.com", MembroEmpresa.Papel.ADMINISTRADOR
    )
    atendente = _membro(
        empresa, "atendente-auditoria@example.com", MembroEmpresa.Papel.ATENDENTE
    )
    _evento(empresa, admin, {"nome": "Auditada", "token": "secreto"})

    cliente = Client()
    cliente.force_login(atendente)
    negada = cliente.get("/api/v1/auditoria/historico")
    cliente.force_login(admin)
    resposta = cliente.get("/api/v1/auditoria/historico?pagina=1&tamanho=10")

    assert negada.status_code == 403
    assert resposta.status_code == 200
    assert resposta.json()["pagina"] == 1
    assert resposta.json()["total"] == 1
    item = resposta.json()["itens"][0]
    assert {"antes", "depois", "snapshot"}.isdisjoint(item)
    assert item["correlacao"] == "corr-api"


@pytest.mark.django_db
def test_restauracao_isola_empresa_e_traduz_conflito_e_validacao() -> None:
    """Distingue revisao externa, snapshot protegido e corpo invalido."""
    from apps.empresas.models import Empresa, MembroEmpresa

    empresa = Empresa.objects.create(nome="Permitida")
    externa = Empresa.objects.create(nome="Externa")
    admin = _membro(
        empresa, "admin-restore@example.com", MembroEmpresa.Papel.ADMINISTRADOR
    )
    admin_externo = _membro(
        externa, "admin-externo@example.com", MembroEmpresa.Papel.ADMINISTRADOR
    )
    revisao_externa = _evento(externa, admin_externo, {"nome": "Externa"}).revisao
    revisao_protegida = _evento(
        empresa, admin, {"nome": "Permitida", "token": "secreto"}, "corr-protegida"
    ).revisao
    cliente = Client()
    cliente.force_login(admin)

    nao_encontrada = cliente.post(
        f"/api/v1/auditoria/revisoes/{revisao_externa.pk}/restaurar",
        data={"correlacao": "corr-404"},
        content_type="application/json",
    )
    conflito = cliente.post(
        f"/api/v1/auditoria/revisoes/{revisao_protegida.pk}/restaurar",
        data={"correlacao": "corr-409"},
        content_type="application/json",
    )
    invalida = cliente.post(
        f"/api/v1/auditoria/revisoes/{revisao_protegida.pk}/restaurar",
        data={},
        content_type="application/json",
    )

    assert nao_encontrada.status_code == 404
    assert conflito.status_code == 409
    assert invalida.status_code == 422
