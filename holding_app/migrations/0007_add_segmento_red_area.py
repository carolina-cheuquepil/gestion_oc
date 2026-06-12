from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("holding_app", "0006_add_sucursal_telefono_area"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                SET @column_exists = (
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'segmento_red'
                      AND COLUMN_NAME = 'sucursal_area_id'
                );

                SET @add_column_sql = IF(
                    @column_exists = 0,
                    'ALTER TABLE segmento_red ADD COLUMN sucursal_area_id INT NULL',
                    'SELECT 1'
                );
                PREPARE add_column_stmt FROM @add_column_sql;
                EXECUTE add_column_stmt;
                DEALLOCATE PREPARE add_column_stmt;

                SET @constraint_exists = (
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'segmento_red'
                      AND CONSTRAINT_NAME = 'fk_segmento_area'
                );

                SET @add_constraint_sql = IF(
                    @constraint_exists = 0,
                    'ALTER TABLE segmento_red ADD CONSTRAINT fk_segmento_area FOREIGN KEY (sucursal_area_id) REFERENCES sucursal_area(sucursal_area_id)',
                    'SELECT 1'
                );
                PREPARE add_constraint_stmt FROM @add_constraint_sql;
                EXECUTE add_constraint_stmt;
                DEALLOCATE PREPARE add_constraint_stmt;
            """,
            reverse_sql="""
                SET @constraint_exists = (
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'segmento_red'
                      AND CONSTRAINT_NAME = 'fk_segmento_area'
                );

                SET @drop_constraint_sql = IF(
                    @constraint_exists > 0,
                    'ALTER TABLE segmento_red DROP FOREIGN KEY fk_segmento_area',
                    'SELECT 1'
                );
                PREPARE drop_constraint_stmt FROM @drop_constraint_sql;
                EXECUTE drop_constraint_stmt;
                DEALLOCATE PREPARE drop_constraint_stmt;

                SET @column_exists = (
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'segmento_red'
                      AND COLUMN_NAME = 'sucursal_area_id'
                );

                SET @drop_column_sql = IF(
                    @column_exists > 0,
                    'ALTER TABLE segmento_red DROP COLUMN sucursal_area_id',
                    'SELECT 1'
                );
                PREPARE drop_column_stmt FROM @drop_column_sql;
                EXECUTE drop_column_stmt;
                DEALLOCATE PREPARE drop_column_stmt;
            """,
        ),
    ]
