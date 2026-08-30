"""Expoe login, logout e emissao de token CSRF."""

from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.utils.http import url_has_allowed_host_and_scheme
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth
from ninja.utils import check_csrf

from apps.contas.api.schemas.autenticacao import (
    LoginEntradaSchema,
    LoginSaidaSchema,
    LogoutSaidaSchema,
    TokenCsrfSaidaSchema,
)
from apps.contas.api.schemas.comum import ErroSaidaSchema, erro
from apps.contas.services.autenticar_usuario import (
    CredenciaisInvalidas,
    MuitasTentativasAutenticacao,
    autenticar_usuario,
)
from apps.contas.services.encerrar_sessao import encerrar_sessao
from apps.empresas.services.empresa_ativa import EmpresaAtivaAusente

router = Router(tags=["autenticacao"])


@router.get("/csrf", response=TokenCsrfSaidaSchema)
def obter_token_csrf(request: HttpRequest) -> dict[str, str]:
    """Emite token e cookie CSRF para clientes da API."""
    return {"csrf_token": get_token(request)}


@router.post(
    "/login",
    response={
        200: LoginSaidaSchema,
        401: ErroSaidaSchema,
        403: ErroSaidaSchema,
        429: ErroSaidaSchema,
    },
)
def login(request: HttpRequest, dados: LoginEntradaSchema):
    """Valida CSRF, delega autenticacao e limita redirects a destinos locais."""
    if check_csrf(request):
        return Status(
            403,
            erro("csrf_invalido", "Token CSRF invalido."),
        )

    try:
        autenticar_usuario(request, dados.email, dados.senha)
    except CredenciaisInvalidas:
        return Status(
            401,
            erro("credenciais_invalidas", "E-mail ou senha invalidos."),
        )
    except EmpresaAtivaAusente:
        return Status(
            403,
            erro("empresa_ativa_ausente", "Nenhuma empresa ativa disponivel."),
        )
    except MuitasTentativasAutenticacao:
        return Status(
            429,
            erro("muitas_tentativas", "Muitas tentativas de autenticacao."),
        )

    destino = "/perfil/"
    if dados.proximo and url_has_allowed_host_and_scheme(
        dados.proximo,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        destino = dados.proximo
    return {"redirecionar_para": destino}


@router.post(
    "/logout",
    auth=SessionAuth(),
    response={200: LogoutSaidaSchema, 401: ErroSaidaSchema, 403: ErroSaidaSchema},
)
def logout(request: HttpRequest) -> dict[str, bool]:
    """Delega o encerramento da sessao autenticada."""
    encerrar_sessao(request)
    return {"encerrada": True}
