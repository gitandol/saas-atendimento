"""Modelo imutavel dos eventos de auditoria."""

from uuid import uuid4

from django.conf import settings
from django.db import models

from apps.auditoria.models.imutavel import ModeloAppendOnly
from apps.auditoria.models.revisao_objeto import RevisaoObjeto
from apps.empresas.models import Empresa


class EventoAuditoria(ModeloAppendOnly):
    """Registra autoria, origem e mudanca vinculada a uma revisao."""

    class Acao(models.TextChoices):
        """Enumera operacoes rastreaveis sobre objetos de dominio."""

        CRIACAO = "CRIACAO", "Criacao"
        ATUALIZACAO = "ATUALIZACAO", "Atualizacao"
        EXCLUSAO = "EXCLUSAO", "Exclusao"
        RESTAURACAO = "RESTAURACAO", "Restauracao"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="eventos_auditoria",
    )
    revisao = models.OneToOneField(
        RevisaoObjeto,
        on_delete=models.PROTECT,
        related_name="evento",
    )
    tipo_objeto = models.CharField(max_length=120)
    objeto_id = models.CharField(max_length=64)
    acao = models.CharField(max_length=12, choices=Acao.choices)
    antes = models.JSONField(default=dict)
    depois = models.JSONField(default=dict)
    campos_alterados = models.JSONField(default=list)
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="eventos_auditoria",
    )
    origem = models.CharField(max_length=80)
    correlacao = models.CharField(max_length=80)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Apresenta primeiro os eventos recentes e protege a manager-base."""

        ordering = ("-criado_em", "-pk")
        base_manager_name = "objects"
        default_manager_name = "objects"
