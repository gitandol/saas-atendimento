"""Expoe os modelos persistentes de auditoria."""

from apps.auditoria.models.evento_auditoria import EventoAuditoria
from apps.auditoria.models.revisao_objeto import RevisaoObjeto

__all__ = ["EventoAuditoria", "RevisaoObjeto"]
