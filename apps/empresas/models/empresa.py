"""Modelo da empresa que representa um tenant da plataforma."""

from uuid import uuid4

from django.db import models


class Empresa(models.Model):
    """Tenant identificado por UUID e exibido pelo nome."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nome = models.CharField(max_length=160)
    segmento = models.CharField(max_length=120, blank=True, default="")
    descricao = models.TextField(max_length=2000, blank=True, default="")
    horario_atendimento = models.CharField(max_length=500, blank=True, default="")
    endereco = models.CharField(max_length=500, blank=True, default="")
    telefone = models.CharField(max_length=30, blank=True, default="")
    site = models.URLField(max_length=500, blank=True, default="")
    instrucoes_atendimento = models.TextField(max_length=4000, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
