"""Adiciona versao otimista ao agregado de conversa."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Versiona transicoes concorrentes de atendimento."""

    dependencies = [("atendimento", "0002_mensagem_processamento_enfileirado_em")]

    operations = [
        migrations.AddField(
            model_name="conversa",
            name="versao",
            field=models.PositiveIntegerField(default=1),
        )
    ]
