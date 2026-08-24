"""Resolve a empresa ativa de uma requisicao de forma isolada por tenant."""

from uuid import UUID

from apps.empresas.models import Empresa, MembroEmpresa

CHAVE_SESSAO_EMPRESA_ATIVA = "empresa_ativa_id"


class EmpresaAtivaAusente(Exception):
    """Indica que a requisicao nao possui uma empresa ativa valida."""


class PermissaoEmpresaNegada(Exception):
    """Indica que o membro ativo nao possui a permissao exigida."""


def _membros_ativos_da_requisicao(request):
    """Retorna as associacoes ativas do usuario autenticado, ordenadas."""
    usuario = getattr(request, "user", None)
    if not getattr(usuario, "is_authenticated", False):
        return MembroEmpresa.objects.none()

    return (
        MembroEmpresa.objects.select_related("empresa")
        .filter(usuario=usuario, ativo=True)
        .order_by("criado_em", "pk")
    )


def _sessao(request):
    """Obtem a sessao quando a requisicao foi preparada pelo middleware Django."""
    return getattr(request, "session", None)


def obter_membro_ativo(request) -> MembroEmpresa | None:
    """Resolve a associacao ativa selecionada ou o primeiro fallback permitido."""
    membros = _membros_ativos_da_requisicao(request)
    sessao = _sessao(request)
    empresa_id = sessao.get(CHAVE_SESSAO_EMPRESA_ATIVA) if sessao is not None else None

    if empresa_id is not None:
        try:
            empresa_id = UUID(str(empresa_id))
        except (AttributeError, TypeError, ValueError):
            sessao.pop(CHAVE_SESSAO_EMPRESA_ATIVA, None)
        else:
            membro = membros.filter(empresa_id=empresa_id).first()
            if membro is not None:
                return membro
            sessao.pop(CHAVE_SESSAO_EMPRESA_ATIVA, None)

    membro = membros.first()
    if membro is not None and sessao is not None:
        sessao[CHAVE_SESSAO_EMPRESA_ATIVA] = str(membro.empresa_id)
    return membro


def obter_empresa_ativa(request) -> Empresa | None:
    """Retorna somente a empresa vinculada ao membro ativo da requisicao."""
    membro = obter_membro_ativo(request)
    return membro.empresa if membro is not None else None


def exigir_empresa_ativa(request) -> Empresa:
    """Exige uma empresa ativa antes de continuar o fluxo solicitado."""
    empresa = obter_empresa_ativa(request)
    if empresa is None:
        raise EmpresaAtivaAusente
    return empresa


def exigir_administrador(request) -> MembroEmpresa:
    """Exige que o membro ativo possua o papel de administrador."""
    membro = obter_membro_ativo(request)
    if membro is None or membro.papel != MembroEmpresa.Papel.ADMINISTRADOR:
        raise PermissaoEmpresaNegada
    return membro
