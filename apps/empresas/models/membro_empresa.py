"""Associacao entre usuario e empresa, com o respectivo papel."""

from django.conf import settings
from django.db import models

from apps.empresas.models.empresa import Empresa


class MembroEmpresa(models.Model):
    """Concede a um usuario um papel de acesso dentro de uma empresa."""

    class Papel(models.TextChoices):
        """Define os papeis de acesso de um membro na empresa."""

        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        ATENDENTE = "ATENDENTE", "Atendente"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membros_empresas",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="membros",
    )
    papel = models.CharField(max_length=13, choices=Papel.choices)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Mantem uma unica associacao por usuario e empresa."""

        constraints = [
            models.UniqueConstraint(
                fields=("usuario", "empresa"),
                name="membro_empresa_usuario_empresa_unico",
            )
        ]
