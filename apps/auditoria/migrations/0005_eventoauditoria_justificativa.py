"""Adiciona justificativa operacional opcional aos eventos."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Preserva a motivacao informada nas transicoes auditadas."""

    dependencies = [("auditoria", "0004_alter_eventoauditoria_ator")]

    operations = [
        migrations.AddField(
            model_name="eventoauditoria",
            name="justificativa",
            field=models.CharField(blank=True, default="", max_length=500),
        )
    ]
