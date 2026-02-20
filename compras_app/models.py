from django.db import models
from django.conf import settings
from decimal import Decimal
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.utils import timezone

# PASO 1° BD: refleja la BD. Estructura

# ----------- Proveedores ------------
class Proveedor(models.Model):
    proveedor_id = models.AutoField(primary_key=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut = models.CharField(max_length=12, unique=True)
    empresa_estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = "proveedor"
    
    def __str__(self):
        return self.razon_social

class Producto(models.Model):
    producto_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(null=True, blank=True)
    tipo_producto =  models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "producto"

    def __str__(self):
        return self.nombre

class ProveedorProducto(models.Model):
    proveedor_producto_id = models.AutoField(primary_key=True)

    proveedor = models.ForeignKey(
        "Proveedor",
        on_delete=models.DO_NOTHING,
        db_column="proveedor_id",
        related_name="proveedor_productos",
    )

    producto = models.ForeignKey(
        "Producto",
        on_delete=models.DO_NOTHING,
        db_column="producto_id",
        related_name="proveedor_productos",
    )

    # Unidad de compra (ej: UN, CAJA, KG). Si quieres, después lo normalizamos a tabla UoM.
    uom_compra = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "proveedor_producto"
        constraints = [
            models.UniqueConstraint(
                fields=["proveedor", "producto"],
                name="uq_proveedor_producto",
            )
        ]

    def __str__(self):
        return f"{self.proveedor_id} - {self.producto_id}"

class ProveedorProductoPrecio(models.Model):
    proveedor_producto_precio_id = models.AutoField(primary_key=True)

    proveedor_producto = models.ForeignKey(
        "ProveedorProducto",
        on_delete=models.DO_NOTHING,
        db_column="proveedor_producto_id",
        related_name="precios",
    )

    precio_neto = models.DecimalField(max_digits=14, decimal_places=2)

    # CLP, USD, etc.
    moneda = models.CharField(max_length=10, default="CLP")

    class Meta:
        managed = False
        db_table = "proveedor_producto_precio"

    def __str__(self):
        return f"{self.proveedor_producto_id} - {self.precio_neto} {self.moneda}"

# ----------- Compras ------------
class TipoDocumento(models.Model):
    tipo_documento_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=40)

    class Meta:
        db_table = "tipo_documento"
        managed = False

    def __str__(self):
        return self.nombre

class EstadoDocumento(models.Model):
    estado_documento_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = "estado_documento"
        managed = False

    def __str__(self):
        return self.nombre

class Moneda(models.Model):
    moneda_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = "moneda"
        managed = False

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Compra(models.Model):
    compra_id = models.AutoField(primary_key=True)

    tipo_documento = models.ForeignKey(
        "TipoDocumento",
        on_delete=models.PROTECT,
        db_column="tipo_documento_id",
        related_name="compras",
    )

    estado_documento = models.ForeignKey(
        "EstadoDocumento",
        on_delete=models.PROTECT,
        db_column="estado_documento_id",
        related_name="compras",
    )

    razon_social = models.ForeignKey(
        "holding_app.Holding",  # o "Holding" si está en la misma app
        on_delete=models.PROTECT,
        db_column="razon_social_id",
        related_name="compras",
    )

    proveedor = models.ForeignKey(
        "Proveedor",
        on_delete=models.PROTECT,
        db_column="proveedor_id",
        related_name="compras",
    )

    folio = models.CharField(max_length=30, null=True, blank=True)
    fecha_emision = models.DateField()
    fecha_requerida = models.DateField(null=True, blank=True)

    moneda = models.ForeignKey(
        "Moneda",
        on_delete=models.PROTECT,
        db_column="moneda_id",
        related_name="compras",
    )

    observacion = models.TextField(null=True, blank=True)

    total_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compra"
        managed = False

    def __str__(self):
        return f"Compra #{self.compra_id} - {self.folio or 'SIN FOLIO'}"

class HistorialCompra(models.Model):
    historial_compra_id = models.AutoField(primary_key=True)

    compra = models.ForeignKey(
        "Compra",
        on_delete=models.CASCADE,
        db_column="compra_id",
        related_name="historial",
    )

    fecha_evento = models.DateTimeField()
    fecha_documento = models.DateField(null=True, blank=True)

    folio = models.CharField(max_length=30, null=True, blank=True)

    tipo_documento = models.ForeignKey(
        "TipoDocumento",
        on_delete=models.PROTECT,
        db_column="tipo_documento_id",
    )
    estado_documento = models.ForeignKey(
        "EstadoDocumento",
        on_delete=models.PROTECT,
        db_column="estado_documento_id",
    )
    archivo = models.FileField(
    upload_to="documentos_compra/",
    null=True,
    blank=True
    )

    class Meta:
        db_table = "historial_compra"
        managed = False
        ordering = ["-fecha_evento"]

class CompraItem(models.Model):
    compra_item_id = models.AutoField(primary_key=True)

    compra = models.ForeignKey(
        "Compra",
        on_delete=models.CASCADE,
        db_column="compra_id",
        related_name="items",
    )

    nro_linea = models.IntegerField(default=1)

    producto = models.ForeignKey(
        "Producto",
        on_delete=models.PROTECT,
        db_column="producto_id",
        null=True,
        blank=True,
        related_name="items_compra",
    )

    descripcion_libre = models.CharField(max_length=255, null=True, blank=True)

    cantidad = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    afecta_iva = models.BooleanField(default=True)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=19.00)

    subtotal_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    subtotal_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    subtotal_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = "compra_item"
        managed = False
        ordering = ["nro_linea"]
        constraints = [
            models.UniqueConstraint(
                fields=["compra", "nro_linea"],
                name="uq_compra_item_linea",
            )
        ]

    def __str__(self):
        nombre = self.producto.nombre if self.producto_id else (self.descripcion_libre or "Ítem")
        return f"Compra {self.compra_id} - Línea {self.nro_linea}: {nombre}"

# ----------- Distribución interna ------------

class FacturaIntercompany(models.Model):
    factura_ic_id = models.AutoField(primary_key=True)

    empresa_emisora = models.ForeignKey(
        "holding_app.Holding",
        on_delete=models.PROTECT,
        db_column="empresa_emisora_id",
        related_name="facturas_ic_emitidas",
    )
    empresa_receptora = models.ForeignKey(
        "holding_app.Holding",
        on_delete=models.PROTECT,
        db_column="empresa_receptora_id",
        related_name="facturas_ic_recibidas",
    )

    # Opcional: referencia a la compra del proveedor (ej. factura AsiaTech 784)
    compra_origen = models.ForeignKey(
        "Compra",
        on_delete=models.PROTECT,
        db_column="compra_origen_id",
        related_name="facturas_ic",
        null=True,
        blank=True,
    )

    folio = models.CharField(max_length=30)
    fecha_emision = models.DateField(default=timezone.now)

    moneda = models.ForeignKey(
        "Moneda",
        on_delete=models.PROTECT,
        db_column="moneda_id",
        related_name="facturas_ic",
    )

    recargo_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00")
    )

    total_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "factura_intercompany"
        managed = False

    def __str__(self):
        return f"Factura IC {self.folio}"

    def recalcular_totales(self, save=True):
        agg = self.items.aggregate(
            neto=Sum("subtotal_neto"),
            iva=Sum("subtotal_iva"),
            total=Sum("subtotal_total"),
        )
        self.total_neto = agg["neto"] or Decimal("0.00")
        self.total_iva = agg["iva"] or Decimal("0.00")
        self.total = agg["total"] or Decimal("0.00")

        if save:
            self.save(update_fields=["total_neto", "total_iva", "total"])

class FacturaIntercompanyItem(models.Model):
    factura_ic_item_id = models.AutoField(primary_key=True)

    factura_ic = models.ForeignKey(
        "FacturaIntercompany",
        on_delete=models.CASCADE,
        db_column="factura_ic_id",
        related_name="items",
    )

    compra_item = models.ForeignKey(
        "CompraItem",
        on_delete=models.PROTECT,
        db_column="compra_item_id",
        related_name="ventas_ic",
    )

    cantidad = models.DecimalField(max_digits=14, decimal_places=3, default=1)

    # costo unitario (base) y venta unitario (base * 1.05)
    precio_base = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    afecta_iva = models.BooleanField(default=True)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("19.00"))

    subtotal_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    subtotal_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    subtotal_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = "factura_intercompany_item"
        managed = False

    def __str__(self):
        return f"IC #{self.factura_ic_id} - CompraItem {self.compra_item_id}"

    # ---------- Helpers ----------
    def vendido_en_otros(self):
        """
        Suma ya vendida (intercompany) por el mismo compra_item, excluyéndome.
        """
        return (
            self.compra_item.ventas_ic
            .exclude(pk=self.pk)
            .aggregate(s=Sum("cantidad"))["s"]
            or Decimal("0.000")
        )

    def saldo_disponible(self):
        return self.compra_item.cantidad - self.vendido_en_otros()

    # ---------- Validación de negocio ----------
    def clean(self):
        errors = {}

        # 1) compra_item obligatorio
        if not self.compra_item_id:
            errors["compra_item"] = "Debes seleccionar un ítem de compra."
            raise ValidationError(errors)

        # 2) cantidad válida
        if self.cantidad is None or self.cantidad <= 0:
            errors["cantidad"] = "La cantidad debe ser mayor a 0."
            raise ValidationError(errors)

        # 3) si hay compra_origen en el header, exigir consistencia
        if self.factura_ic_id and self.factura_ic.compra_origen_id:
            if self.compra_item.compra_id != self.factura_ic.compra_origen_id:
                raise ValidationError("El ítem no pertenece a la compra origen de esta factura.")

        # 4) validar saldo disponible (sin crashear)
        vendido = (
            FacturaIntercompanyItem.objects
            .filter(compra_item_id=self.compra_item_id)
            .exclude(pk=self.pk)
            .aggregate(s=Sum("cantidad"))["s"] or Decimal("0.000")
        )

        disponible = (self.compra_item.cantidad or Decimal("0.000")) - vendido

        if self.cantidad > disponible:
            errors["cantidad"] = f"La cantidad excede el saldo disponible. Disponible: {disponible}"
            raise ValidationError(errors)

    # ---------- Cálculo automático ----------
    def save(self, *args, **kwargs):
        # Validar reglas
        self.full_clean()

        # Determinar precio_base desde compra_item si viene en cero
        if (self.precio_base is None) or (self.precio_base == 0):
            self.precio_base = self.compra_item.precio_unitario or Decimal("0.00")

        recargo = (self.factura_ic.recargo_porcentaje or Decimal("5.00")) / Decimal("100")
        self.precio_venta = (self.precio_base * (Decimal("1.00") + recargo)).quantize(Decimal("0.01"))

        # Neto (venta): cantidad * precio_venta, aplicando descuento si algún día lo agregas
        neto = (Decimal(self.cantidad) * self.precio_venta).quantize(Decimal("0.01"))

        iva = Decimal("0.00")
        if self.afecta_iva:
            iva = (neto * (self.iva_porcentaje / Decimal("100"))).quantize(Decimal("0.01"))

        self.subtotal_neto = neto
        self.subtotal_iva = iva
        self.subtotal_total = (neto + iva).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

        # Recalcular totales del encabezado (opcional pero recomendable)
        self.factura_ic.recalcular_totales(save=True)
