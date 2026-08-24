"""Testes do mascaramento recursivo de dados sensiveis."""


def test_sanitiza_chaves_sensiveis_em_estruturas_aninhadas() -> None:
    """Impede que segredos diretos ou aninhados persistam no snapshot."""
    from apps.auditoria.services.sanitizar_snapshot import sanitizar_snapshot

    snapshot = {
        "senha": "texto",
        "Token": "bearer",
        "perfil": {
            "segredo": "interno",
            "api_key": "externa",
            "chave_api": "alternativa",
            "nome": "Cliente",
        },
        "itens": [{"token": "item", "valor": 7}],
    }

    assert sanitizar_snapshot(snapshot) == {
        "senha": "[PROTEGIDO]",
        "Token": "[PROTEGIDO]",
        "perfil": {
            "segredo": "[PROTEGIDO]",
            "api_key": "[PROTEGIDO]",
            "chave_api": "[PROTEGIDO]",
            "nome": "Cliente",
        },
        "itens": [{"token": "[PROTEGIDO]", "valor": 7}],
    }
