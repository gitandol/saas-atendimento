"""Expoe topicos autenticados de ajuda contextual."""

from dataclasses import asdict

from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.ajuda.api.schemas.topico import ErroAjudaSchema, TopicoSaidaSchema
from apps.ajuda.services.renderizar_markdown import renderizar_markdown

router = Router(tags=["ajuda"], auth=SessionAuth())


@router.get("/{slug}", response={200: TopicoSaidaSchema, 404: ErroAjudaSchema})
def obter_topico(request: HttpRequest, slug: str):
    """Renderiza o Markdown solicitado ou oculta caminhos inexistentes."""
    try:
        return asdict(renderizar_markdown(slug))
    except (FileNotFoundError, OSError):
        return Status(
            404,
            {"codigo": "topico_nao_encontrado", "mensagem": "Topico nao encontrado."},
        )
