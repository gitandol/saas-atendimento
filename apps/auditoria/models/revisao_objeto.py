"""Modelo de snapshots sequenciais dos objetos auditados."""

from django.db import models

from apps.auditoria.models.imutavel import ModeloAppendOnly
from apps.empresas.models import Empresa


class RevisaoObjeto(ModeloAppendOnly):
    """Preserva um estado sanitizado e numerado de um objeto da empresa."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="revisoes_objetos",
    )
    tipo_objeto = models.CharField(max_length=120)
    objeto_id = models.CharField(max_length=64)
    numero = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena, numera e protege o historico do objeto."""

        ordering = ("-numero", "-criado_em")
        base_manager_name = "objects"
        default_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "tipo_objeto", "objeto_id", "numero"),
                name="revisao_objeto_numero_unico",
            )
        ]
