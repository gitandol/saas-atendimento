"""Testes da leitura e sanitizacao de Markdown funcional."""

from pathlib import Path


def test_renderiza_markdown_sem_script_e_com_data(tmp_path: Path) -> None:
    """Entrega HTML seguro e informa a atualizacao do arquivo fonte."""
    from apps.ajuda.services.renderizar_markdown import renderizar_markdown

    arquivo = tmp_path / "topico.md"
    arquivo.write_text(
        "# Titulo\n\nTexto com **destaque**.<script>alert(1)</script>",
        encoding="utf-8",
    )

    topico = renderizar_markdown("topico", diretorio=tmp_path)

    assert topico.titulo == "Titulo"
    assert "<strong>destaque</strong>" in topico.html
    assert "<script" not in topico.html.casefold()
    assert "alert(1)" not in topico.html
    assert topico.atualizado_em.tzinfo is not None
