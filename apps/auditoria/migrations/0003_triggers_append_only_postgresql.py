"""Protege eventos e revisoes contra UPDATE ou DELETE no PostgreSQL."""

from django.db import migrations

FUNCAO = "auditoria_impedir_mutacao_historica"
TABELAS = ("auditoria_eventoauditoria", "auditoria_revisaoobjeto")


def criar_triggers_append_only(_apps, schema_editor) -> None:
    """Instala triggers apenas no banco de producao PostgreSQL."""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        f"""
        CREATE FUNCTION {FUNCAO}() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Registros de auditoria sao imutaveis.';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for tabela in TABELAS:
        schema_editor.execute(
            f"""
            CREATE TRIGGER {tabela}_append_only
            BEFORE UPDATE OR DELETE ON {tabela}
            FOR EACH ROW EXECUTE FUNCTION {FUNCAO}();
            """
        )


def remover_triggers_append_only(_apps, schema_editor) -> None:
    """Remove triggers e funcao para permitir reversao controlada."""
    if schema_editor.connection.vendor != "postgresql":
        return
    for tabela in TABELAS:
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS {tabela}_append_only ON {tabela};"
        )
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {FUNCAO}();")


class Migration(migrations.Migration):
    """Adiciona defesa append-only no banco PostgreSQL."""

    dependencies = [("auditoria", "0002_alter_eventoauditoria_options_and_more")]

    operations = [
        migrations.RunPython(
            criar_triggers_append_only,
            remover_triggers_append_only,
        )
    ]
