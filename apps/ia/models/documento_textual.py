"""Modelo de documento textual controlado por empresa."""

from django.db import models

from apps.empresas.models import Empresa


class DocumentoTextual(models.Model):
    """Armazena conhecimento textual ordenavel e sujeito a exclusao logica."""

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="documentos_textuais"
    )
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField(max_length=50000)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)
    excluido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        """Define ordem deterministica por empresa."""

        ordering = ("ordem", "pk")
        indexes = [
            models.Index(
                fields=("empresa", "excluido_em", "ativo", "ordem"),
                name="ia_doc_contexto_idx",
            )
        ]
