"""Modelo da empresa que representa um tenant da plataforma."""

from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.db import models


def validar_fuso_horario(valor: str) -> None:
    """Recusa identificadores que nao pertencem ao banco IANA."""
    try:
        ZoneInfo(valor)
    except (KeyError, ValueError, ZoneInfoNotFoundError) as erro:
        raise ValidationError("Fuso horario invalido.") from erro


class Empresa(models.Model):
    """Tenant identificado por UUID e exibido pelo nome."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nome = models.CharField(max_length=160)
    fuso_horario = models.CharField(
        max_length=64,
        default="America/Rio_Branco",
        validators=(validar_fuso_horario,),
    )
    segmento = models.CharField(max_length=120, blank=True, default="")
    descricao = models.TextField(max_length=2000, blank=True, default="")
    horario_atendimento = models.CharField(max_length=500, blank=True, default="")
    endereco = models.CharField(max_length=500, blank=True, default="")
    telefone = models.CharField(max_length=30, blank=True, default="")
    site = models.URLField(max_length=500, blank=True, default="")
    instrucoes_atendimento = models.TextField(max_length=4000, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
