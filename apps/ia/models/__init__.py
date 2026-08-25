"""Expoe os modelos do modulo de inteligencia artificial."""

from apps.ia.models.configuracao_ia import ConfiguracaoIA
from apps.ia.models.documento_textual import DocumentoTextual
from apps.ia.models.pergunta_frequente import PerguntaFrequente

__all__ = ["ConfiguracaoIA", "DocumentoTextual", "PerguntaFrequente"]
