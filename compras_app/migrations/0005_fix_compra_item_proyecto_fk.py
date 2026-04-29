from django.db import migrations


def fix_compra_item_proyecto_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    db_name = schema_editor.connection.settings_dict["NAME"]

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'compra_item'
              AND COLUMN_NAME = 'proyecto_id'
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """,
            [db_name],
        )
        constraints = cursor.fetchall()

        has_target_fk = False
        for constraint_name, referenced_table in constraints:
            if referenced_table == "proyecto_informatica":
                has_target_fk = True
                continue

            cursor.execute(
                f"ALTER TABLE compra_item DROP FOREIGN KEY `{constraint_name}`"
            )

        if not has_target_fk:
            cursor.execute(
                """
                ALTER TABLE compra_item
                ADD CONSTRAINT fk_compra_item_proyecto
                FOREIGN KEY (proyecto_id)
                REFERENCES proyecto_informatica (proyecto_id)
                """
            )


class Migration(migrations.Migration):

    dependencies = [
        ("compras_app", "0004_compraitem_facturaintercompany_and_more"),
    ]

    operations = [
        migrations.RunPython(
            fix_compra_item_proyecto_fk,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
