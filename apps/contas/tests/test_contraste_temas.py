"""Testes matematicos do contraste das paletas visuais."""

import re
from pathlib import Path

import pytest


def _rgb(cor: str) -> tuple[int, int, int]:
    """Converte uma cor hexadecimal em canais RGB."""
    valor = cor.removeprefix("#")
    return tuple(int(valor[indice : indice + 2], 16) for indice in (0, 2, 4))


def _luminancia(cor: str) -> float:
    """Calcula luminancia relativa conforme WCAG."""
    canais = []
    for canal in _rgb(cor):
        normalizado = canal / 255
        canais.append(
            normalizado / 12.92
            if normalizado <= 0.04045
            else ((normalizado + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * canais[0] + 0.7152 * canais[1] + 0.0722 * canais[2]


def _contraste(primeira: str, segunda: str) -> float:
    """Retorna a razao de contraste entre duas cores."""
    clara, escura = sorted(
        (_luminancia(primeira), _luminancia(segunda)),
        reverse=True,
    )
    return (clara + 0.05) / (escura + 0.05)


def _bloco(css: str, seletor: str) -> str:
    """Extrai declaracoes do seletor informado."""
    encontrado = re.search(rf"{re.escape(seletor)}\s*\{{([^}}]+)\}}", css)
    assert encontrado is not None, f"Seletor ausente: {seletor}"
    return encontrado.group(1)


def _token(bloco: str, nome: str) -> str:
    """Extrai uma cor hexadecimal de um bloco CSS."""
    encontrado = re.search(rf"--{nome}:\s*(#[0-9a-fA-F]{{6}})", bloco)
    assert encontrado is not None, f"Token ausente: {nome}"
    return encontrado.group(1)


@pytest.mark.parametrize("tema", ["azul", "esmeralda", "violeta", "rubi", "ambar"])
def test_cor_primaria_dark_atende_contraste_wcag_aa(tema: str) -> None:
    """Exige contraste AA para texto e conteudo sobre a cor primaria."""
    css = Path("static/src/css/temas.css").read_text(encoding="utf-8")
    superficie = _token(_bloco(css, ":root.dark"), "cor-superficie")
    bloco_tema = _bloco(css, f':root.dark[data-tema="{tema}"]')
    primaria = _token(bloco_tema, "cor-primaria")
    sobre_primaria = _token(bloco_tema, "cor-em-primaria")

    assert _contraste(primaria, superficie) >= 4.5
    assert _contraste(primaria, sobre_primaria) >= 4.5
