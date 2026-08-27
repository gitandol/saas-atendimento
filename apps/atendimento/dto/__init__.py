"""Expoe os DTOs imutaveis do atendimento."""

from apps.atendimento.dto.contato import ContatoDTO
from apps.atendimento.dto.conversa import ConversaDTO
from apps.atendimento.dto.mensagem import MensagemDTO

__all__ = ["ContatoDTO", "ConversaDTO", "MensagemDTO"]
