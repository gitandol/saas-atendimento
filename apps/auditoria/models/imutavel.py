"""Fornece protecao append-only compartilhada pela trilha de auditoria."""

from django.core.exceptions import ValidationError
from django.db import models


class QuerySetAppendOnly(models.QuerySet):
    """Bloqueia atalhos de mutacao em massa da ORM."""

    def update(self, **kwargs):
        """Recusa atualizacao em massa de registros historicos."""
        raise ValidationError("Registros de auditoria sao imutaveis.")

    def delete(self):
        """Recusa exclusao em massa de registros historicos."""
        raise ValidationError("Registros de auditoria nao podem ser excluidos.")

    def bulk_update(self, objs, fields, batch_size=None):
        """Recusa atualizacao em lote que contornaria save da instancia."""
        raise ValidationError("Registros de auditoria sao imutaveis.")

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        """Recusa insercao em lote que contornaria validacoes da instancia."""
        raise ValidationError("Registros devem ser criados individualmente.")


class ManagerAppendOnly(models.Manager.from_queryset(QuerySetAppendOnly)):
    """Expoe o QuerySet protegido como manager publica e manager-base."""


class ModeloAppendOnly(models.Model):
    """Permite insercao inicial e rejeita alteracao ou exclusao posterior."""

    objects = ManagerAppendOnly()

    class Meta:
        """Mantem a base abstrata fora do esquema do banco."""

        abstract = True

    def save(self, *args, **kwargs) -> None:
        """Permite somente a insercao inicial do registro."""
        if not self._state.adding:
            raise ValidationError("Registros de auditoria sao imutaveis.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Recusa exclusao direta do registro historico."""
        raise ValidationError("Registros de auditoria nao podem ser excluidos.")
