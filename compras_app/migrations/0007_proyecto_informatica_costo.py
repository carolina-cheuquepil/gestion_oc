from django.db import migrations


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS proyecto_informatica_costo (
    proyecto_costo_id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_informatica_id INT NOT NULL,
    compra_item_id INT NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    cantidad DECIMAL(14, 3) NOT NULL DEFAULT 1.000,
    costo_unitario DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    creado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_proyecto_informatica_costo_compra_item (compra_item_id),
    KEY idx_proyecto_informatica_costo_proyecto (proyecto_informatica_id),
    CONSTRAINT fk_pic_proyecto
        FOREIGN KEY (proyecto_informatica_id)
        REFERENCES proyecto_informatica (proyecto_informatica_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pic_compra_item
        FOREIGN KEY (compra_item_id)
        REFERENCES compra_item (compra_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


DROP_TABLE_SQL = "DROP TABLE IF EXISTS proyecto_informatica_costo;"


class Migration(migrations.Migration):

    dependencies = [
        ("compras_app", "0006_remove_compra_item_proyecto"),
    ]

    operations = [
        migrations.RunSQL(CREATE_TABLE_SQL, DROP_TABLE_SQL),
    ]
