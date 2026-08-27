"""Modelo de conversa entre a empresa e um contato."""

from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.atendimento.models.contato import Contato
from apps.empresas.models import Empresa


class Conversa(models.Model):
    """Agrupa mensagens e o estado operacional de um atendimento."""

    class Modo(models.TextChoices):
        """Define quem conduz a conversa."""

        IA = "IA", "IA"
        HUMANO = "HUMANO", "Humano"

    class Estado(models.TextChoices):
        """Define se a conversa aceita continuidade operacional."""

        ABERTA = "ABERTA", "Aberta"
        FINALIZADA = "FINALIZADA", "Finalizada"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="conversas",
    )
    contato = models.ForeignKey(
        Contato,
        on_delete=models.PROTECT,
        related_name="conversas",
    )
    modo = models.CharField(max_length=7, choices=Modo.choices, default=Modo.IA)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ABERTA,
    )
    atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="conversas_atendidas",
    )
    ultima_mensagem = models.ForeignKey(
        "atendimento.Mensagem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    contagem_nao_lida = models.PositiveIntegerField(default=0)
    finalizada_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        """Exige que contato e ultima mensagem pertencam ao agregado."""
        super().clean()
        if self.contato_id and self.contato.empresa_id != self.empresa_id:
            raise ValidationError(
                {"contato": "O contato deve pertencer a empresa da conversa."}
            )
        if self.ultima_mensagem_id and (
            self.ultima_mensagem.empresa_id != self.empresa_id
            or self.ultima_mensagem.conversa_id != self.id
        ):
            raise ValidationError(
                {
                    "ultima_mensagem": (
                        "A ultima mensagem deve pertencer a propria conversa."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        """Valida as fronteiras do tenant antes de persistir pelo ORM."""
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        """Mantem uma conversa aberta por contato e otimiza a caixa de entrada."""

        ordering = ("-atualizado_em", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "contato"),
                condition=Q(estado="ABERTA"),
                name="atend_conversa_aberta_unica",
            )
        ]
        indexes = [
            models.Index(
                fields=("empresa", "estado", "-atualizado_em", "-id"),
                name="atend_conversa_lista_idx",
            )
        ]
