"""Modelo da empresa que representa um tenant da plataforma."""

from uuid import uuid4

from django.db import models


class Empresa(models.Model):
    """Tenant identificado por UUID e exibido pelo nome."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nome = models.CharField(max_length=160)
    criado_em = models.DateTimeField(auto_now_add=True)
