"""Modelo de pergunta frequente controlada por empresa."""

from django.db import models

from apps.empresas.models import Empresa


class PerguntaFrequente(models.Model):
    """Armazena uma pergunta e resposta ordenavel com exclusao logica."""

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="perguntas_frequentes"
    )
    pergunta = models.CharField(max_length=500)
    resposta = models.TextField(max_length=10000)
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
                name="ia_faq_contexto_idx",
            )
        ]
