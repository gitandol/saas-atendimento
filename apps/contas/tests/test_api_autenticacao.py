"""Testes HTTP da API de autenticacao."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import Client

from apps.contas.models import Usuario
from apps.contas.services.autenticar_usuario import MuitasTentativasAutenticacao
from apps.empresas.models import Empresa, MembroEmpresa


def _token_csrf(cliente: Client) -> str:
    """Obtem token e cookie CSRF pelo endpoint publico."""
    resposta = cliente.get("/api/v1/autenticacao/csrf")
    assert resposta.status_code == 200
    assert resposta.cookies["csrftoken"].value
    return resposta.json()["csrf_token"]


def _criar_membro(email: str = "admin@example.com") -> Usuario:
    """Cria usuario com credenciais e empresa ativa para testes HTTP."""
    usuario = Usuario.objects.create_user(email=email, password="senha")
    empresa = Empresa.objects.create(nome="Empresa HTTP")
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ADMINISTRADOR,
    )
    return usuario


@pytest.mark.django_db
def test_login_exige_csrf_real_antes_de_delegar() -> None:
    """Recusa login sem CSRF mesmo quando o schema e valido."""
    cliente = Client(enforce_csrf_checks=True)

    with patch(
        "apps.contas.api.endpoints.autenticacao.autenticar_usuario"
    ) as autenticar:
        resposta = cliente.post(
            "/api/v1/autenticacao/login",
            {"email": "admin@example.com", "senha": "senha"},
            content_type="application/json",
        )

    assert resposta.status_code == 403
    assert autenticar.call_count == 0


@pytest.mark.django_db
def test_login_valido_cria_sessao_e_retorna_destino_padrao() -> None:
    """Autentica membro ativo com token CSRF valido."""
    usuario = _criar_membro()
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    resposta = cliente.post(
        "/api/v1/autenticacao/login",
        {"email": usuario.email, "senha": "senha"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"redirecionar_para": "/perfil/"}
    assert cliente.session["_auth_user_id"] == str(usuario.pk)


@pytest.mark.django_db
def test_login_delega_credenciais_e_aceita_destino_local_seguro() -> None:
    """Repassa credenciais ao service e preserva redirect local seguro."""
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    with patch(
        "apps.contas.api.endpoints.autenticacao.autenticar_usuario"
    ) as autenticar:
        resposta = cliente.post(
            "/api/v1/autenticacao/login",
            {
                "email": "pessoa@example.com",
                "senha": "segredo",
                "proximo": "/perfil/?secao=dados",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    assert resposta.status_code == 200
    assert resposta.json() == {"redirecionar_para": "/perfil/?secao=dados"}
    requisicao, email, senha = autenticar.call_args.args
    assert requisicao.path == "/api/v1/autenticacao/login"
    assert email == "pessoa@example.com"
    assert senha == "segredo"


@pytest.mark.django_db
def test_login_descarta_redirect_externo() -> None:
    """Evita open redirect depois de credenciais validas."""
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    with patch("apps.contas.api.endpoints.autenticacao.autenticar_usuario"):
        resposta = cliente.post(
            "/api/v1/autenticacao/login",
            {
                "email": "pessoa@example.com",
                "senha": "segredo",
                "proximo": "https://malicioso.example/roubar",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    assert resposta.status_code == 200
    assert resposta.json() == {"redirecionar_para": "/perfil/"}


@pytest.mark.django_db
def test_login_rejeita_schema_malformado_com_422() -> None:
    """Retorna validacao Ninja para payload sem senha."""
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    resposta = cliente.post(
        "/api/v1/autenticacao/login",
        {"email": "pessoa@example.com"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert resposta.status_code == 422


@pytest.mark.django_db
def test_login_traduz_credenciais_invalidas_em_401() -> None:
    """Nao revela qual credencial falhou."""
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    resposta = cliente.post(
        "/api/v1/autenticacao/login",
        {"email": "inexistente@example.com", "senha": "incorreta"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "credenciais_invalidas"


@pytest.mark.django_db
def test_login_traduz_empresa_ativa_ausente_em_403() -> None:
    """Recusa usuario valido sem associacao ativa."""
    usuario = Usuario.objects.create_user(
        email="sem-empresa@example.com", password="senha"
    )
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    resposta = cliente.post(
        "/api/v1/autenticacao/login",
        {"email": usuario.email, "senha": "senha"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_ativa_ausente"


@pytest.mark.django_db
def test_login_traduz_limite_de_tentativas_em_429() -> None:
    """Explicita throttling do service no contrato HTTP."""
    cache.clear()
    cliente = Client(enforce_csrf_checks=True)
    token = _token_csrf(cliente)

    with patch(
        "apps.contas.api.endpoints.autenticacao.autenticar_usuario",
        side_effect=MuitasTentativasAutenticacao,
    ):
        resposta = cliente.post(
            "/api/v1/autenticacao/login",
            {"email": "limite@example.com", "senha": "incorreta"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    assert resposta.status_code == 429
    assert resposta.json()["codigo"] == "muitas_tentativas"


@pytest.mark.django_db
def test_logout_autenticado_exige_csrf_e_delega_encerramento() -> None:
    """Encerra a sessao somente com autenticacao e CSRF validos."""
    usuario = _criar_membro("sair@example.com")
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(usuario)

    sem_token = cliente.post("/api/v1/autenticacao/logout")
    assert sem_token.status_code == 403

    token = _token_csrf(cliente)
    with patch("apps.contas.api.endpoints.autenticacao.encerrar_sessao") as encerrar:
        resposta = cliente.post(
            "/api/v1/autenticacao/logout",
            HTTP_X_CSRFTOKEN=token,
        )

    assert resposta.status_code == 200
    assert resposta.json() == {"encerrada": True}
    assert encerrar.call_count == 1
    assert encerrar.call_args.args[0].user == usuario
