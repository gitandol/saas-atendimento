"""Valida as fronteiras de importacao da arquitetura modular."""

import ast
import subprocess
import tomllib
from pathlib import Path

import pytest


def test_contratos_do_import_linter_sao_respeitados() -> None:
    """Executa os contratos declarados para as camadas existentes."""
    resultado = subprocess.run(
        ["lint-imports", "--config", "pyproject.toml"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def _modulos_importados(caminho: Path) -> set[str]:
    """Extrai imports absolutos de um modulo Python sem executa-lo."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    modulos: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


def _arquivos_python(camada: str) -> list[Path]:
    """Localiza modulos de uma camada em todos os aplicativos."""
    return sorted(Path("apps").glob(f"*/{camada}/**/*.py"))


@pytest.mark.parametrize("camada", ["api", "views"])
def test_camada_http_nao_importa_models(camada: str) -> None:
    """Bloqueia acesso direto a models nas fronteiras HTTP."""
    importacoes = {
        modulo
        for arquivo in _arquivos_python(camada)
        for modulo in _modulos_importados(arquivo)
    }
    proibidas = {modulo for modulo in importacoes if ".models" in modulo}
    assert proibidas == set()


def test_services_nao_importam_api_ou_views() -> None:
    """Mantem regras de negocio independentes das fronteiras HTTP."""
    importacoes = {
        modulo
        for arquivo in _arquivos_python("services")
        for modulo in _modulos_importados(arquivo)
    }
    proibidas = {
        modulo for modulo in importacoes if ".api" in modulo or ".views" in modulo
    }
    assert proibidas == set()


def test_contratos_declaram_apps_de_contas_e_empresas() -> None:
    """Mantem novos dominios cobertos pelos limites do import-linter."""
    with Path("pyproject.toml").open("rb") as arquivo:
        contratos = tomllib.load(arquivo)["tool"]["importlinter"]["contracts"]

    fontes_por_nome = {
        contrato["name"]: set(contrato["source_modules"]) for contrato in contratos
    }

    assert fontes_por_nome["Camadas HTTP nao importam models"] >= {
        "apps.contas.api",
        "apps.contas.views",
    }
    assert fontes_por_nome["Services nao importam fronteiras HTTP"] >= {
        "apps.contas.services",
        "apps.empresas.services",
    }
