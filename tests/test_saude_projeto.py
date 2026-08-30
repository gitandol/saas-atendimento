"""Verifica se a fundacao Django inicia com configuracoes de teste."""


def test_verificacao_de_saude_responde_ok(cliente):
    """Confirma que a aplicacao pronta responde sem consultar servicos externos."""
    resposta = cliente.get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"estado": "ok"}


def test_dependencia_externa_degrada_sem_alterar_liveness(cliente) -> None:
    """Separa disponibilidade do processo da saude de fornecedores."""
    from apps.nucleo.services.verificacoes import verificar_dependencias

    def indisponivel() -> None:
        """Simula uma fronteira externa indisponivel."""
        raise ConnectionError

    resultado = verificar_dependencias(
        sondas={
            "banco": lambda: None,
            "redis": lambda: None,
            "worker": lambda: None,
            "openai": indisponivel,
            "evolution": indisponivel,
        }
    )

    assert resultado.estado == "degradado"
    assert resultado.componentes == {
        "banco": "ok",
        "redis": "ok",
        "worker": "ok",
        "openai": "degradado",
        "evolution": "degradado",
    }
    assert cliente.get("/api/v1/saude").status_code == 200


def test_endpoint_publica_saude_separada_das_dependencias(cliente, monkeypatch) -> None:
    """Permite ao monitor identificar banco, Redis e worker separadamente."""
    from apps.nucleo.services.verificacoes import EstadoDependencias

    monkeypatch.setattr(
        "apps.nucleo.api.endpoints.saude.verificar_dependencias",
        lambda: EstadoDependencias(
            estado="degradado",
            componentes={
                "banco": "ok",
                "redis": "degradado",
                "worker": "ok",
            },
        ),
    )

    resposta = cliente.get("/api/v1/saude/dependencias")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "estado": "degradado",
        "componentes": {
            "banco": "ok",
            "redis": "degradado",
            "worker": "ok",
        },
    }
