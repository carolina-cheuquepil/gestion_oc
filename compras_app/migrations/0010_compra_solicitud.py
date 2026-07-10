from django.db import migrations


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS compra_solicitud (
    token CHAR(32) PRIMARY KEY,
    compra_id INT UNSIGNED NULL,
    creado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_compra_solicitud_compra (compra_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


DROP_TABLE_SQL = "DROP TABLE IF EXISTS compra_solicitud;"


class Migration(migrations.Migration):

    dependencies = [
        ("compras_app", "0009_historial_factura_clp"),
    ]

    operations = [
        migrations.RunSQL(CREATE_TABLE_SQL, DROP_TABLE_SQL),
    ]
