"""Separa mensagens nao respondidas das mensagens ainda nao lidas."""

from django.db import migrations, models


def preencher_contagem_nao_respondida(apps, schema_editor) -> None:
    """Conta em lote as entradas sem uma resposta visivel posterior."""
    Conversa = apps.get_model("atendimento", "Conversa")
    Mensagem = apps.get_model("atendimento", "Mensagem")
    citar = schema_editor.connection.ops.quote_name
    tabela_conversa = citar(Conversa._meta.db_table)
    tabela_mensagem = citar(Mensagem._meta.db_table)
    schema_editor.execute(
        f"""
        UPDATE {tabela_conversa} AS conversa
        SET contagem_nao_respondida = (
            SELECT COUNT(*)
            FROM {tabela_mensagem} AS entrada
            WHERE entrada.conversa_id = conversa.id
              AND entrada.direcao = 'ENTRADA'
              AND NOT EXISTS (
                  SELECT 1
                  FROM {tabela_mensagem} AS resposta
                  WHERE resposta.conversa_id = conversa.id
                    AND resposta.direcao = 'SAIDA'
                    AND resposta.autor IN ('IA', 'ATENDENTE')
                    AND (
                        resposta.criado_em > entrada.criado_em
                        OR (
                            resposta.criado_em = entrada.criado_em
                            AND resposta.id > entrada.id
                        )
                    )
              )
        )
        """
    )


class Migration(migrations.Migration):
    """Adiciona e preenche o agregado usado pelo badge da caixa de entrada."""

    dependencies = [("atendimento", "0003_conversa_versao")]

    operations = [
        migrations.AddField(
            model_name="conversa",
            name="contagem_nao_respondida",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(
            preencher_contagem_nao_respondida,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
