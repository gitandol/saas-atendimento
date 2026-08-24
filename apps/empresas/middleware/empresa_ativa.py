"""Anexa a empresa ativa validada a cada requisicao autenticada."""

from apps.empresas.services.empresa_ativa import obter_membro_ativo


class EmpresaAtivaMiddleware:
    """Disponibiliza a associacao e a empresa ativa para o restante da requisicao."""

    def __init__(self, get_response):
        """Armazena o proximo componente da cadeia de resposta."""
        self.get_response = get_response

    def __call__(self, request):
        """Anexa a resolucao validada antes de delegar a requisicao."""
        membro = obter_membro_ativo(request)
        request.membro_empresa_ativo = membro
        request.empresa_ativa = membro.empresa if membro is not None else None
        return self.get_response(request)
