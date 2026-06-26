from django.db import migrations


FORWARD_SQL = """
ALTER TABLE historial_compra
    ADD COLUMN factura_total_neto_clp DECIMAL(14, 2) NULL,
    ADD COLUMN factura_total_iva_clp DECIMAL(14, 2) NULL,
    ADD COLUMN factura_total_clp DECIMAL(14, 2) NULL;
"""


REVERSE_SQL = """
ALTER TABLE historial_compra
    DROP COLUMN factura_total_neto_clp,
    DROP COLUMN factura_total_iva_clp,
    DROP COLUMN factura_total_clp;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("compras_app", "0008_correo_destinatario"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
