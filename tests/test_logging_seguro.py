"""Valida a allowlist de valores operacionais dos logs."""

import json
import logging

from config.logging import FormatadorJsonSeguro


def test_formatador_omite_identificador_com_texto_livre() -> None:
    """Nao permite que payload arbitrario seja publicado como identificador."""
    registro = logging.LogRecord(
        "teste",
        logging.WARNING,
        __file__,
        1,
        "payload_invalido",
        (),
        None,
    )
    registro.mensagem_id = "telefone ou texto privado"
    registro.resultado = "rejeitado"

    dados = json.loads(FormatadorJsonSeguro().format(registro))

    assert "mensagem_id" not in dados
    assert dados["resultado"] == "rejeitado"
    assert "telefone ou texto privado" not in dados.values()
