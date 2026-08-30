"""Testes do mascaramento recursivo de dados sensiveis."""

import json


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


def test_sanitiza_dados_pessoais_e_conteudo_de_atendimento() -> None:
    """Evita persistir telefone, mensagem ou fonte do prompt em auditoria."""
    from apps.auditoria.services.sanitizar_snapshot import sanitizar_snapshot

    snapshot = {
        "telefone": "telefone-privado",
        "numero_telefone": "numero-privado",
        "numero_normalizado": "normalizado-privado",
        "texto": "mensagem-privada",
        "conteudo": "conteudo-privado",
        "prompt": "prompt-privado",
        "instrucoes_atendimento": "instrucao-privada",
        "nome": "Dado operacional permitido",
    }

    protegido = sanitizar_snapshot(snapshot)

    assert protegido == {
        **{chave: "[PROTEGIDO]" for chave in snapshot if chave != "nome"},
        "nome": "Dado operacional permitido",
    }


def test_protege_revisao_restauravel_sem_persistir_conteudo_aberto() -> None:
    """Cifra dados restauraveis e mantem credenciais irrecuperaveis."""
    from apps.auditoria.services.sanitizar_snapshot import (
        proteger_snapshot_restauravel,
        restaurar_snapshot_protegido,
    )

    snapshot = {
        "telefone": "telefone-privado",
        "conteudo": "conteudo-privado",
        "instrucoes_atendimento": "instrucao-privada",
        "token": "credencial-irrecuperavel",
        "nome": "Dado operacional permitido",
    }

    protegido = proteger_snapshot_restauravel(snapshot)
    serializado = json.dumps(protegido)

    assert snapshot["telefone"] not in serializado
    assert snapshot["conteudo"] not in serializado
    assert snapshot["instrucoes_atendimento"] not in serializado
    assert protegido["token"] == "[PROTEGIDO]"
    assert restaurar_snapshot_protegido(protegido) == {
        "telefone": snapshot["telefone"],
        "conteudo": snapshot["conteudo"],
        "instrucoes_atendimento": snapshot["instrucoes_atendimento"],
        "token": "[PROTEGIDO]",
        "nome": snapshot["nome"],
    }
