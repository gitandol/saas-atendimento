"""Testes do contrato OpenAPI da restauracao."""


def test_restauracao_declara_resposta_422_de_validacao() -> None:
    """Mantem documentado o JSON de validacao emitido pelo Django Ninja."""
    from config.api import api

    contrato = api.get_openapi_schema()
    respostas = contrato["paths"]["/api/v1/auditoria/revisoes/{revisao_id}/restaurar"][
        "post"
    ]["responses"]

    assert 422 in respostas
