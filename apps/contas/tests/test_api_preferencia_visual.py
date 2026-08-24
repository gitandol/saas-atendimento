"""Testes HTTP da preferencia visual autenticada."""

import pytest
from django.test import Client

from apps.contas.models import PreferenciaVisual, Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _cliente_autenticado() -> tuple[Client, Usuario, Empresa]:
    """Cria cliente com uma empresa ativa valida."""
    empresa = Empresa.objects.create(nome="Empresa API Visual")
    usuario = Usuario.objects.create_user(email="tema@example.com", password="senha")
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ADMINISTRADOR,
    )
    cliente = Client()
    cliente.force_login(usuario)
    return cliente, usuario, empresa


@pytest.mark.django_db
def test_put_aceita_cada_tema_e_modo_do_contrato() -> None:
    """Aceita exclusivamente as combinacoes declaradas pela fronteira HTTP."""
    cliente, usuario, empresa = _cliente_autenticado()
    temas = ["azul", "esmeralda", "violeta", "rubi", "ambar"]
    modos = ["CLARO", "ESCURO", "SISTEMA"]

    for indice, tema in enumerate(temas):
        modo = modos[indice % len(modos)]
        resposta = cliente.put(
            "/api/v1/preferencias/visual",
            data={"tema": tema, "modo": modo},
            content_type="application/json",
        )
        assert resposta.status_code == 200
        assert resposta.json() == {"tema": tema, "modo": modo}

    preferencia = PreferenciaVisual.objects.get(usuario=usuario, empresa=empresa)
    assert (preferencia.tema, preferencia.modo) == ("ambar", "ESCURO")


@pytest.mark.django_db
def test_get_recupera_preferencia_persistida_apos_novo_login() -> None:
    """Restaura a personalizacao do usuario autenticado no tenant ativo."""
    cliente, usuario, empresa = _cliente_autenticado()
    PreferenciaVisual.objects.create(
        usuario=usuario,
        empresa=empresa,
        tema="rubi",
        modo="ESCURO",
    )

    cliente.logout()
    cliente.force_login(usuario)
    resposta = cliente.get("/api/v1/preferencias/visual")

    assert resposta.status_code == 200
    assert resposta.json() == {"tema": "rubi", "modo": "ESCURO"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("tema", "modo"),
    [("laranja", "CLARO"), ("azul", "NOTURNO")],
)
def test_put_recusa_tema_ou_modo_fora_do_contrato(tema: str, modo: str) -> None:
    """Devolve erro de validacao sem persistir valores desconhecidos."""
    cliente, _usuario, _empresa = _cliente_autenticado()

    resposta = cliente.put(
        "/api/v1/preferencias/visual",
        data={"tema": tema, "modo": modo},
        content_type="application/json",
    )

    assert resposta.status_code == 422
    assert PreferenciaVisual.objects.count() == 0


@pytest.mark.django_db
def test_put_exige_usuario_autenticado() -> None:
    """Impede visitante de persistir preferencia no servidor."""
    resposta = Client().put(
        "/api/v1/preferencias/visual",
        data={"tema": "azul", "modo": "SISTEMA"},
        content_type="application/json",
    )

    assert resposta.status_code == 401
