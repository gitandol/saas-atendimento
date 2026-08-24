"""Preferencia de paleta e luminosidade por usuario e empresa."""

from django.conf import settings
from django.db import models

from apps.empresas.models import Empresa


class PreferenciaVisual(models.Model):
    """Mantem a personalizacao visual isolada no tenant do usuario."""

    class Tema(models.TextChoices):
        """Enumera as cinco paletas disponiveis."""

        AZUL = "azul", "Azul"
        ESMERALDA = "esmeralda", "Esmeralda"
        VIOLETA = "violeta", "Violeta"
        RUBI = "rubi", "Rubi"
        AMBAR = "ambar", "Ambar"

    class Modo(models.TextChoices):
        """Enumera as estrategias de luminosidade."""

        CLARO = "CLARO", "Claro"
        ESCURO = "ESCURO", "Escuro"
        SISTEMA = "SISTEMA", "Sistema"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="preferencias_visuais",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferencias_visuais",
    )
    tema = models.CharField(
        max_length=10,
        choices=Tema.choices,
        default=Tema.AZUL,
    )
    modo = models.CharField(
        max_length=7,
        choices=Modo.choices,
        default=Modo.SISTEMA,
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        """Impede mais de uma preferencia no mesmo escopo."""

        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "usuario"),
                name="preferencia_visual_empresa_usuario_unica",
            )
        ]
