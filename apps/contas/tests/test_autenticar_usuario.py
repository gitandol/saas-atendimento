"""Testes do servico de autenticacao de usuarios."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.http import HttpRequest
from django.test import RequestFactory

from apps.contas.models import Usuario
from apps.contas.services.autenticar_usuario import (
    CredenciaisInvalidas,
    MuitasTentativasAutenticacao,
    _chave_tentativas,
    autenticar_usuario,
    reservar_tentativa_autenticacao,
)
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.empresa_ativa import EmpresaAtivaAusente


@pytest.fixture
def requisicao_factory():
    """Monta requisicoes anonimas com sessao."""

    def criar():
        """Cria uma requisicao anonima independente."""
        requisicao = RequestFactory().post("/", REMOTE_ADDR="198.51.100.10")
        requisicao.session = SessionStore()
        requisicao.user = AnonymousUser()
        return requisicao

    return criar


def usuario_habilitado(email):
    """Cria usuario com associacao ativa."""
    usuario = Usuario.objects.create_user(email=email, password="senha")
    empresa = Empresa.objects.create(nome="Empresa")
    MembroEmpresa.objects.create(
        usuario=usuario, empresa=empresa, papel=MembroEmpresa.Papel.ATENDENTE
    )
    return usuario


@pytest.mark.django_db
def test_autentica_usuario_com_credenciais_validas(requisicao_factory):
    """Autentica credencial valida de membro ativo."""
    usuario = usuario_habilitado("pessoa@example.com")
    requisicao = requisicao_factory()

    assert autenticar_usuario(requisicao, "pessoa@EXAMPLE.COM", "senha") == usuario
    assert requisicao.user == usuario
    assert requisicao.session.get("_auth_user_id") == str(usuario.pk)


@pytest.mark.django_db
def test_autentica_preservando_maiusculas_do_local_part(
    requisicao_factory: Callable[[], HttpRequest],
) -> None:
    """Preserva o local-part e normaliza somente o dominio para autenticar."""
    usuario = usuario_habilitado("Pessoa@Example.com")

    autenticado = autenticar_usuario(
        requisicao_factory(), "Pessoa@EXAMPLE.COM", "senha"
    )

    assert autenticado == usuario


@pytest.mark.django_db
def test_rejeita_credenciais_invalidas(requisicao_factory):
    """Nao cria sessao para senha incorreta."""
    usuario = usuario_habilitado("invalida@example.com")

    with pytest.raises(CredenciaisInvalidas):
        autenticar_usuario(requisicao_factory(), usuario.email, "incorreta")


@pytest.mark.django_db
def test_rejeita_membro_inativo_sem_criar_sessao(requisicao_factory):
    """Bloqueia credencial valida sem associacao ativa."""
    usuario = Usuario.objects.create_user(email="inativo@example.com", password="senha")
    empresa = Empresa.objects.create(nome="Inativa")
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ATENDENTE,
        ativo=False,
    )
    requisicao = requisicao_factory()

    with pytest.raises(EmpresaAtivaAusente):
        autenticar_usuario(requisicao, usuario.email, "senha")
    assert not requisicao.user.is_authenticated
    assert requisicao.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_bloqueia_sexta_falha_em_cinco_minutos(requisicao_factory):
    """Mantem cinco CredenciaisInvalidas antes do bloqueio."""
    usuario = usuario_habilitado("limite@example.com")

    for _ in range(5):
        with pytest.raises(CredenciaisInvalidas):
            autenticar_usuario(requisicao_factory(), usuario.email, "incorreta")
    with pytest.raises(MuitasTentativasAutenticacao):
        autenticar_usuario(requisicao_factory(), usuario.email, "incorreta")


@pytest.mark.django_db
def test_sucesso_reinicia_contador_de_tentativas(requisicao_factory):
    """Permite cinco novas falhas depois do login."""
    usuario = usuario_habilitado("reset@example.com")
    with pytest.raises(CredenciaisInvalidas):
        autenticar_usuario(requisicao_factory(), usuario.email, "incorreta")

    autenticar_usuario(requisicao_factory(), usuario.email, "senha")

    for _ in range(5):
        with pytest.raises(CredenciaisInvalidas):
            autenticar_usuario(requisicao_factory(), usuario.email, "incorreta")
    with pytest.raises(MuitasTentativasAutenticacao):
        autenticar_usuario(requisicao_factory(), usuario.email, "incorreta")


def _resultado_da_tentativa_reservada(chave: str) -> type[Exception]:
    """Classifica o resultado que a camada de autenticacao retornaria."""
    try:
        reservar_tentativa_autenticacao(chave)
    except MuitasTentativasAutenticacao:
        return MuitasTentativasAutenticacao
    return CredenciaisInvalidas


@pytest.mark.django_db
def test_reserva_concorrente_bloqueia_exatamente_a_sexta_tentativa():
    """Reserva no cache antes da autenticacao mesmo sob seis chamadas paralelas."""
    cache.clear()
    chave = _chave_tentativas("concorrente@example.com", "198.51.100.20")

    with ThreadPoolExecutor(max_workers=6) as executor:
        resultados = list(executor.map(_resultado_da_tentativa_reservada, [chave] * 6))

    assert resultados.count(CredenciaisInvalidas) == 5
    assert resultados.count(MuitasTentativasAutenticacao) == 1


@pytest.mark.django_db
def test_chave_do_throttle_oculta_dados_brutos_e_separa_origens():
    """Gera chaves opacas diferentes para combinacoes distintas."""
    email = "pessoa@example.com"
    endereco = "198.51.100.30"
    chave = _chave_tentativas(email, endereco)

    assert email not in chave
    assert endereco not in chave
    assert chave != _chave_tentativas("outra@example.com", endereco)
    assert chave != _chave_tentativas(email, "198.51.100.31")
