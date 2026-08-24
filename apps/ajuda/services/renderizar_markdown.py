"""Le Markdown funcional e produz um subconjunto seguro de HTML."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from django.conf import settings

PADRAO_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PADRAO_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
PADRAO_DESTAQUE = re.compile(r"\*\*(.+?)\*\*")


@dataclass(frozen=True, slots=True)
class TopicoAjuda:
    """Transporta o conteudo seguro e seus metadados de exibicao."""

    slug: str
    titulo: str
    html: str
    atualizado_em: datetime


def _html_seguro(markdown: str) -> tuple[str, str]:
    """Converte titulos, paragrafos e destaque depois de remover scripts."""
    sem_scripts = PADRAO_SCRIPT.sub("", markdown)
    blocos = [bloco.strip() for bloco in sem_scripts.split("\n\n") if bloco.strip()]
    titulo = "Ajuda"
    html: list[str] = []
    for bloco in blocos:
        linhas = bloco.splitlines()
        if linhas[0].startswith("# "):
            conteudo = escape(linhas[0][2:].strip())
            titulo = conteudo
            html.append(f"<h1>{conteudo}</h1>")
            linhas = linhas[1:]
            if not linhas:
                continue
        texto = " ".join(linha.strip() for linha in linhas)
        texto = PADRAO_DESTAQUE.sub(r"<strong>\1</strong>", escape(texto))
        html.append(f"<p>{texto}</p>")
    return titulo, "\n".join(html)


def renderizar_markdown(slug: str, *, diretorio: Path | None = None) -> TopicoAjuda:
    """Le somente um slug valido dentro do diretorio funcional configurado."""
    if not PADRAO_SLUG.fullmatch(slug):
        raise FileNotFoundError(slug)
    raiz = diretorio or (settings.BASE_DIR / "docs" / "funcionalidades")
    caminho = raiz / f"{slug}.md"
    markdown = caminho.read_text(encoding="utf-8")
    titulo, html = _html_seguro(markdown)
    atualizado_em = datetime.fromtimestamp(caminho.stat().st_mtime, tz=UTC)
    return TopicoAjuda(
        slug=slug,
        titulo=titulo,
        html=html,
        atualizado_em=atualizado_em,
    )
