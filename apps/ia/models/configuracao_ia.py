"""Modelo da configuracao de inteligencia artificial por empresa."""

from django.db import models

from apps.empresas.models import Empresa


class ConfiguracaoIA(models.Model):
    """Mantem uma configuracao de IA isolada para cada empresa."""

    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name="configuracao_ia",
    )
    modelo = models.CharField(max_length=120, default="gpt-4.1-mini")
    nome_assistente = models.CharField(max_length=120, blank=True, default="")
    personalidade = models.TextField(max_length=4000, blank=True, default="")
    mensagem_saudacao = models.TextField(max_length=1000, blank=True, default="")
    mensagem_falha = models.TextField(max_length=1000, blank=True, default="")
    respostas_automaticas_ativas = models.BooleanField(default=False)
    chave_api_criptografada = models.TextField(blank=True, default="", editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __repr__(self) -> str:
        """Representa a configuracao sem incluir qualquer credencial."""
        return f"ConfiguracaoIA(empresa_id={self.empresa_id!r})"
