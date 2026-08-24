"""Verifica se a fundacao Django inicia com configuracoes de teste."""


def test_verificacao_de_saude_responde_ok(cliente):
    """Confirma que a aplicacao pronta responde sem consultar servicos externos."""
    resposta = cliente.get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"estado": "ok"}
