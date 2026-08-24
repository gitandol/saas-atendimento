"""Constroi o perfil do usuario no contexto de uma empresa permitida."""

from dataclasses import dataclass
from uuid import UUID

from django.http import HttpRequest

from apps.empresas.models import MembroEmpresa
from apps.empresas.services.consultas import obter_empresa_permitida
from apps.empresas.services.empresa_ativa import EmpresaAtivaAusente, obter_membro_ativo


@dataclass(frozen=True)
class PerfilUsuario:
    """Dados do usuario e de seu papel na empresa consultada."""

    email: str
    nome: str
    empresa_id: UUID
    empresa_nome: str
    papel: str
    pode_administrar: bool


def _perfil_do_membro(membro: MembroEmpresa) -> PerfilUsuario:
    """Converte a associacao ativa no perfil exposto pelo servico."""
    usuario = membro.usuario
    return PerfilUsuario(
        email=usuario.email,
        nome=usuario.get_full_name(),
        empresa_id=membro.empresa_id,
        empresa_nome=membro.empresa.nome,
        papel=membro.papel,
        pode_administrar=membro.papel == MembroEmpresa.Papel.ADMINISTRADOR,
    )


def obter_perfil(request: HttpRequest, empresa_id: UUID | None = None) -> PerfilUsuario:
    """Retorna o perfil na empresa ativa ou em UUID explicitamente permitido."""
    membro = obter_membro_ativo(request)
    if membro is None:
        raise EmpresaAtivaAusente

    if empresa_id is None:
        return _perfil_do_membro(membro)

    empresa = obter_empresa_permitida(request.user, empresa_id)
    membro = MembroEmpresa.objects.select_related("usuario", "empresa").get(
        usuario=request.user,
        empresa=empresa,
        ativo=True,
    )
    return _perfil_do_membro(membro)
