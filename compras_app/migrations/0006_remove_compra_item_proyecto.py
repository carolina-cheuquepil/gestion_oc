from django.db import migrations


def remove_compra_item_proyecto(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    db_name = schema_editor.connection.settings_dict["NAME"]

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'compra_item'
              AND COLUMN_NAME = 'proyecto_id'
            """,
            [db_name],
        )
        if cursor.fetchone()[0] == 0:
            return

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'compra_item'
              AND COLUMN_NAME = 'proyecto_id'
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """,
            [db_name],
        )
        for (constraint_name,) in cursor.fetchall():
            cursor.execute(
                f"ALTER TABLE compra_item DROP FOREIGN KEY `{constraint_name}`"
            )

        cursor.execute("ALTER TABLE compra_item DROP COLUMN proyecto_id")


class Migration(migrations.Migration):

    dependencies = [
        ("compras_app", "0005_fix_compra_item_proyecto_fk"),
    ]

    operations = [
        migrations.RunPython(
            remove_compra_item_proyecto,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
