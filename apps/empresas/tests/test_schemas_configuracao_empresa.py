"""Testes dos contratos HTTP da configuracao da empresa."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


def _dados_validos() -> dict[str, object]:
    """Monta uma entrada completa com valores literais validos."""
    return {
        "nome": "Empresa Exemplo",
        "segmento": "Servicos",
        "descricao": "Descricao institucional",
        "horario_atendimento": "Segunda a sexta, 8h as 18h",
        "endereco": "Rua Principal, 100",
        "telefone": "+55 (68) 99999-0000",
        "site": "https://empresa.example.com",
        "instrucoes_atendimento": "Seja objetivo.",
        "atualizado_em": datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
    }


def test_schema_de_entrada_valida_e_normaliza_o_contrato_completo() -> None:
    """Normaliza telefone e aceita todos os campos editaveis e a versao."""
    from apps.empresas.api.schemas.configuracao_empresa import EmpresaEntradaSchema

    schema = EmpresaEntradaSchema.model_validate(_dados_validos())

    assert schema.nome == "Empresa Exemplo"
    assert schema.telefone == "+5568999990000"
    assert schema.site == "https://empresa.example.com"
    assert schema.atualizado_em == datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("nome", "x" * 161),
        ("segmento", "x" * 121),
        ("descricao", "x" * 2001),
        ("horario_atendimento", "x" * 501),
        ("endereco", "x" * 501),
        ("telefone", "x" * 31),
        ("site", "https://example.com/" + "x" * 481),
        ("instrucoes_atendimento", "x" * 4001),
    ],
)
def test_schema_de_entrada_rejeita_campos_acima_do_limite(
    campo: str, valor: str
) -> None:
    """Recusa payload que ultrapassa qualquer limite persistido."""
    from apps.empresas.api.schemas.configuracao_empresa import EmpresaEntradaSchema

    dados = _dados_validos()
    dados[campo] = valor

    with pytest.raises(ValidationError):
        EmpresaEntradaSchema.model_validate(dados)


def test_schema_de_entrada_rejeita_site_sem_url_http() -> None:
    """Impede endereco de site sem protocolo HTTP valido."""
    from apps.empresas.api.schemas.configuracao_empresa import EmpresaEntradaSchema

    dados = _dados_validos()
    dados["site"] = "empresa.example.com"

    with pytest.raises(ValidationError):
        EmpresaEntradaSchema.model_validate(dados)


def test_schema_de_saida_expoe_configuracao_e_versao() -> None:
    """Mantem a resposta completa necessaria para recarregar o formulario."""
    from apps.empresas.api.schemas.configuracao_empresa import EmpresaSaidaSchema

    schema = EmpresaSaidaSchema.model_validate(_dados_validos())

    assert schema.model_dump() == _dados_validos()
