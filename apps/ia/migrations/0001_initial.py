"""Cria a configuracao de IA isolada por empresa."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Persiste a configuracao unica de IA para cada empresa."""

    initial = True
    dependencies = [("empresas", "0002_configuracao_empresa")]
    operations = [
        migrations.CreateModel(
            name="ConfiguracaoIA",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modelo", models.CharField(default="gpt-4.1-mini", max_length=120)),
                (
                    "nome_assistente",
                    models.CharField(blank=True, default="", max_length=120),
                ),
                (
                    "personalidade",
                    models.TextField(blank=True, default="", max_length=4000),
                ),
                (
                    "mensagem_saudacao",
                    models.TextField(blank=True, default="", max_length=1000),
                ),
                (
                    "mensagem_falha",
                    models.TextField(blank=True, default="", max_length=1000),
                ),
                ("respostas_automaticas_ativas", models.BooleanField(default=False)),
                (
                    "chave_api_criptografada",
                    models.TextField(blank=True, default="", editable=False),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "empresa",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configuracao_ia",
                        to="empresas.empresa",
                    ),
                ),
            ],
        )
    ]
