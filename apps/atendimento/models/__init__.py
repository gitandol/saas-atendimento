"""Expoe os modelos centrais do atendimento."""

from apps.atendimento.models.contato import Contato
from apps.atendimento.models.conversa import Conversa
from apps.atendimento.models.mensagem import Mensagem

__all__ = ["Contato", "Conversa", "Mensagem"]
