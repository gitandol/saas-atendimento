"""Autentica usuarios com limitacao de tentativas por origem."""

from hashlib import sha256

from django.contrib.auth import authenticate, login
from django.core.cache import cache
from django.http import HttpRequest

from apps.contas.models import Usuario
from apps.empresas.models import MembroEmpresa
from apps.empresas.services.empresa_ativa import EmpresaAtivaAusente

LIMITE_TENTATIVAS = 5
JANELA_TENTATIVAS_SEGUNDOS = 300


class CredenciaisInvalidas(Exception):
    """Indica que e-mail ou senha informados nao sao validos."""


class MuitasTentativasAutenticacao(Exception):
    """Indica que a origem excedeu o limite de falhas de autenticacao."""


def _normalizar_email(email: str) -> str:
    """Normaliza o dominio sem alterar o local-part usado na autenticacao."""
    return Usuario.objects.normalize_email(email.strip())


def _endereco_cliente(request: HttpRequest) -> str:
    """Obtem o endereco informado pelo servidor HTTP para a requisicao."""
    return request.META.get("REMOTE_ADDR", "")


def _chave_tentativas(email: str, endereco_cliente: str) -> str:
    """Cria chave de cache sem expor e-mail ou endereco em texto puro."""
    dados = f"{email}:{endereco_cliente}".encode()
    digest = sha256(dados).hexdigest()
    return f"autenticacao:tentativas:{digest}"


def reservar_tentativa_autenticacao(chave: str) -> None:
    """Reserva uma tentativa antes de autenticar, bloqueando alem do limite."""
    while True:
        if cache.add(chave, 1, timeout=JANELA_TENTATIVAS_SEGUNDOS):
            return

        try:
            tentativas = cache.incr(chave)
        except ValueError:
            continue

        if tentativas > LIMITE_TENTATIVAS:
            raise MuitasTentativasAutenticacao
        return


def autenticar_usuario(request: HttpRequest, email: str, senha: str) -> Usuario:
    """Autentica um membro ativo e cria sua sessao Django."""
    email_normalizado = _normalizar_email(email)
    chave = _chave_tentativas(email_normalizado.casefold(), _endereco_cliente(request))

    reservar_tentativa_autenticacao(chave)

    usuario = authenticate(request, email=email_normalizado, password=senha)
    if usuario is None:
        raise CredenciaisInvalidas

    if not MembroEmpresa.objects.filter(usuario=usuario, ativo=True).exists():
        raise EmpresaAtivaAusente

    login(request, usuario)
    cache.delete(chave)
    return usuario
