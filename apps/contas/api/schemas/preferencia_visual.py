"""Contratos HTTP da personalizacao visual."""

from typing import Literal

from ninja import Schema

TemaVisual = Literal["azul", "esmeralda", "violeta", "rubi", "ambar"]
ModoVisual = Literal["CLARO", "ESCURO", "SISTEMA"]


class PreferenciaVisualEntradaSchema(Schema):
    """Valida os valores aceitos para uma atualizacao."""

    tema: TemaVisual
    modo: ModoVisual


class PreferenciaVisualSaidaSchema(Schema):
    """Expoe a preferencia efetiva do usuario."""

    tema: TemaVisual
    modo: ModoVisual
