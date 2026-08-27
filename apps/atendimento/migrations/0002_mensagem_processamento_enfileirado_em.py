"""Adiciona o marcador de publicacao Celery das mensagens recebidas."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Inclui controle recuperavel sem alterar mensagens ja persistidas."""

    dependencies = [
        ("atendimento", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mensagem",
            name="processamento_enfileirado",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="mensagem",
            name="processamento_enfileirado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
