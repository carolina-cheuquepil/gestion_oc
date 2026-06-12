from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("holding_app", "0004_create_segmento_red"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS sucursal_area (
                    sucursal_area_id INT NOT NULL AUTO_INCREMENT,
                    sucursal_id INT NOT NULL,
                    area VARCHAR(100) NOT NULL,
                    tipo VARCHAR(30) NULL,
                    activa TINYINT(1) NOT NULL DEFAULT 1,
                    PRIMARY KEY (sucursal_area_id),
                    CONSTRAINT fk_area_sucursal
                        FOREIGN KEY (sucursal_id)
                        REFERENCES sucursal(sucursal_id)
                );
            """,
            reverse_sql="DROP TABLE IF EXISTS sucursal_area;",
        ),
    ]
