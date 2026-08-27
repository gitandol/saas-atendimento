"""Modelo de contato atendido por uma empresa."""

from uuid import uuid4

from django.db import models

from apps.empresas.models import Empresa


class Contato(models.Model):
    """Identifica um cliente por numero normalizado dentro do tenant."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="contatos",
    )
    nome = models.CharField(max_length=160, blank=True, default="")
    numero_normalizado = models.CharField(max_length=30)
    observacoes = models.TextField(max_length=2000, blank=True, default="")
    primeiro_contato_em = models.DateTimeField(null=True, blank=True)
    ultimo_contato_em = models.DateTimeField(null=True, blank=True)
    excluido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        """Garante identidade por tenant e acelera busca de contatos ativos."""

        ordering = ("nome", "numero_normalizado", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "numero_normalizado"),
                name="atend_contato_empresa_numero_unico",
            )
        ]
        indexes = [
            models.Index(
                fields=("empresa", "excluido_em", "numero_normalizado"),
                name="atend_contato_busca_idx",
            )
        ]
