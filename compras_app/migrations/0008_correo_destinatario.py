from django.db import migrations


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS correo_destinatario (
    correo_destinatario_id INT AUTO_INCREMENT PRIMARY KEY,
    tipo VARCHAR(40) NOT NULL,
    nombre VARCHAR(100) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    actualizado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_correo_destinatario_tipo_email (tipo, email),
    KEY idx_correo_destinatario_tipo_activo (tipo, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


DROP_TABLE_SQL = "DROP TABLE IF EXISTS correo_destinatario;"


class Migration(migrations.Migration):

    dependencies = [
        ("compras_app", "0007_proyecto_informatica_costo"),
    ]

    operations = [
        migrations.RunSQL(CREATE_TABLE_SQL, DROP_TABLE_SQL),
    ]
