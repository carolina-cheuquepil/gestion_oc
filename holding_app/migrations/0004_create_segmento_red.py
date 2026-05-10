from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("holding_app", "0003_alter_holding_table"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS segmento_red (
                    segmento_red_id INT NOT NULL AUTO_INCREMENT,
                    sucursal_id INT NOT NULL,
                    segmento VARCHAR(50) NOT NULL,
                    segmento_nombre VARCHAR(100) NOT NULL,
                    activa TINYINT(1) NOT NULL DEFAULT 1,
                    PRIMARY KEY (segmento_red_id),
                    CONSTRAINT fk_segmento_red_sucursal
                        FOREIGN KEY (sucursal_id)
                        REFERENCES sucursal(sucursal_id)
                );
            """,
            reverse_sql="DROP TABLE IF EXISTS segmento_red;",
        ),
    ]
