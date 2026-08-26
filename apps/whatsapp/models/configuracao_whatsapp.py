"""Modelo da configuracao Evolution por empresa."""

from django.db import models

from apps.empresas.models import Empresa
from apps.whatsapp.integrations.protocolos import EstadoConexao


class ConfiguracaoWhatsApp(models.Model):
    """Mantem uma unica instancia de WhatsApp isolada por empresa."""

    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name="configuracao_whatsapp",
    )
    url_base = models.URLField(max_length=500)
    nome_instancia = models.CharField(max_length=120)
    chave_api_criptografada = models.TextField(blank=True, default="", editable=False)
    ativo = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=20,
        choices=[(estado.value, estado.value) for estado in EstadoConexao],
        default=EstadoConexao.DESCONECTADO.value,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __repr__(self) -> str:
        """Representa a configuracao sem incluir qualquer credencial."""
        return f"ConfiguracaoWhatsApp(empresa_id={self.empresa_id!r})"
