"""Valida estabilidade, autenticacao e respostas seguras do OpenAPI."""

import re

from config.api import api

_METODOS = {"get", "post", "put", "patch", "delete"}
_PUBLICAS = {
    ("/api/v1/autenticacao/csrf", "get"),
    ("/api/v1/autenticacao/login", "post"),
    ("/api/v1/saude", "get"),
    ("/api/v1/saude/dependencias", "get"),
    ("/api/v1/webhooks/evolution/{empresa_id}/{token}/", "post"),
}
_CAMPOS_SENSIVEIS = {
    "senha",
    "chave_api",
    "token",
    "segredo",
    "prompt",
    "numero_telefone",
}


def _operacoes(schema: dict) -> list[tuple[str, str, dict]]:
    """Extrai operacoes HTTP reais do documento OpenAPI."""
    return [
        (caminho, metodo, operacao)
        for caminho, item in schema["paths"].items()
        for metodo, operacao in item.items()
        if metodo in _METODOS
    ]


def _propriedades_resposta(schema: dict, operacao: dict) -> set[str]:
    """Resolve propriedades de schemas usados somente nas respostas 2xx."""
    propriedades: set[str] = set()
    componentes = schema.get("components", {}).get("schemas", {})
    for status, resposta in operacao.get("responses", {}).items():
        if not str(status).startswith("2"):
            continue
        conteudo = resposta.get("content", {}).get("application/json", {})
        atual = conteudo.get("schema", {})
        referencia = atual.get("$ref")
        if referencia:
            atual = componentes[referencia.rsplit("/", 1)[-1]]
        propriedades.update(atual.get("properties", {}))
    return propriedades


def test_operation_ids_sao_unicos_deterministicos_e_estaveis() -> None:
    """Evita colisao ou sufixos aleatorios que quebram clientes gerados."""
    schema = api.get_openapi_schema()
    ids = [operacao["operationId"] for _, _, operacao in _operacoes(schema)]

    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9_]+", operation_id) for operation_id in ids)
    assert ids == [
        operacao["operationId"]
        for _, _, operacao in _operacoes(api.get_openapi_schema())
    ]


def test_operacoes_internas_exigem_sessao_e_mutacoes_documentam_erros() -> None:
    """Mantem publicas somente as fronteiras explicitamente autorizadas."""
    for caminho, metodo, operacao in _operacoes(api.get_openapi_schema()):
        if (caminho, metodo) in _PUBLICAS:
            continue
        assert operacao.get("security") == [{"SessionAuth": []}], (caminho, metodo)
        if metodo != "get":
            assert any(
                str(status).startswith("4") for status in operacao.get("responses", {})
            ), (caminho, metodo)


def test_respostas_de_sucesso_nao_expoem_campos_sensiveis() -> None:
    """Impede que schemas de saida publiquem credenciais ou identificadores crus."""
    schema = api.get_openapi_schema()
    for caminho, metodo, operacao in _operacoes(schema):
        proibidos = _propriedades_resposta(schema, operacao) & _CAMPOS_SENSIVEIS
        assert proibidos == set(), (caminho, metodo, proibidos)
