"""Modelo das mensagens persistidas em uma conversa."""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.empresas.models import Empresa


class Mensagem(models.Model):
    """Registra conteudo textual, autoria, entrega e idempotencia externa."""

    class Direcao(models.TextChoices):
        """Define o sentido da mensagem em relacao a plataforma."""

        ENTRADA = "ENTRADA", "Entrada"
        SAIDA = "SAIDA", "Saida"

    class Autor(models.TextChoices):
        """Define o agente que originou a mensagem."""

        CLIENTE = "CLIENTE", "Cliente"
        IA = "IA", "IA"
        ATENDENTE = "ATENDENTE", "Atendente"
        SISTEMA = "SISTEMA", "Sistema"

    class Status(models.TextChoices):
        """Define o estagio de recebimento ou entrega da mensagem."""

        RECEBIDA = "RECEBIDA", "Recebida"
        PENDENTE = "PENDENTE", "Pendente"
        ENVIADA = "ENVIADA", "Enviada"
        ENTREGUE = "ENTREGUE", "Entregue"
        FALHA = "FALHA", "Falha"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="mensagens",
    )
    conversa = models.ForeignKey(
        "atendimento.Conversa",
        on_delete=models.PROTECT,
        related_name="mensagens",
    )
    direcao = models.CharField(max_length=7, choices=Direcao.choices)
    autor = models.CharField(max_length=9, choices=Autor.choices)
    texto = models.TextField(max_length=4096)
    identificador_externo = models.CharField(max_length=160, blank=True, default="")
    status = models.CharField(max_length=8, choices=Status.choices)
    erro_sanitizado = models.CharField(max_length=500, blank=True, default="")
    enviado_em = models.DateTimeField(null=True, blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    processamento_enfileirado = models.BooleanField(default=False)
    processamento_enfileirado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        """Recusa texto de saida vazio mesmo quando contem apenas espacos."""
        super().clean()
        if self.direcao == self.Direcao.SAIDA and not self.texto.strip():
            raise ValidationError({"texto": "O texto da mensagem e obrigatorio."})
        if self.direcao == self.Direcao.SAIDA and len(self.texto) > 4096:
            raise ValidationError({"texto": "O texto excede 4.096 caracteres."})
        if self.conversa_id and self.conversa.empresa_id != self.empresa_id:
            raise ValidationError(
                {"conversa": "A conversa deve pertencer a empresa da mensagem."}
            )

    def save(self, *args, **kwargs) -> None:
        """Valida as fronteiras do tenant antes de persistir pelo ORM."""
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        """Ordena o historico e impede duplicacao de eventos externos."""

        ordering = ("criado_em", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "identificador_externo"),
                condition=~Q(identificador_externo=""),
                name="atend_mensagem_externa_unica",
            )
        ]
        indexes = [
            models.Index(
                fields=("empresa", "conversa", "criado_em", "id"),
                name="atend_mensagem_hist_idx",
            )
        ]
