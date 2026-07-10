from django.db import models

# PASO 1°: refleja la BD. Estructura
class Holding(models.Model):
    empresa_id = models.AutoField(primary_key=True)
    codigo_empresa = models.IntegerField(unique=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut_numero = models.IntegerField(unique=True)
    rut_dv = models.CharField(max_length=1, blank=True, null=True)
    empresa_estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = "md_empresa"
    
    def __str__(self):
        return self.nombre or self.razon_social


class Direccion(models.Model):
    direccion_id = models.AutoField(primary_key=True)
    calle = models.CharField(max_length=255)
    numero = models.CharField(max_length=20, null=True, blank=True)
    complemento = models.CharField(max_length=255, null=True, blank=True)
    ciudad = models.CharField(max_length=100)
    comuna = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "md_direccion"

    def __str__(self):
        partes = [self.calle]
        if self.numero:
            partes.append(self.numero)
        if self.complemento:
            partes.append(self.complemento)
        if self.ciudad:
            partes.append(self.ciudad)
        return ", ".join(partes)


class Sucursal(models.Model):
    sucursal_id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(
        Holding,
        on_delete=models.CASCADE,
        db_column="empresa_id",
        related_name="sucursales",
    )
    codigo_sucursal = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255)
    activa = models.BooleanField(default=True, null=True)
    direccion = models.ForeignKey(
        Direccion,
        on_delete=models.SET_NULL,
        db_column="direccion_id",
        related_name="sucursales",
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "md_sucursal"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class SucursalTelefono(models.Model):
    sucursal_telefono_id = models.AutoField(primary_key=True)
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        db_column="sucursal_id",
        related_name="telefonos",
    )
    sucursal_area = models.ForeignKey(
        "SucursalArea",
        on_delete=models.SET_NULL,
        db_column="sucursal_area_id",
        related_name="telefonos",
        blank=True,
        null=True,
    )
    tipo_telefono = models.CharField(max_length=30, blank=True, null=True)
    numero = models.CharField(max_length=20)
    principal = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "r_sucursal_telefono"
        ordering = ["-principal", "tipo_telefono", "numero"]

    def __str__(self):
        tipo = f"{self.tipo_telefono}: " if self.tipo_telefono else ""
        principal = " (principal)" if self.principal else ""
        return f"{tipo}{self.numero}{principal}"


class SucursalArea(models.Model):
    sucursal_area_id = models.AutoField(primary_key=True)
    sucursal_piso = models.ForeignKey(
        "SucursalPiso",
        on_delete=models.CASCADE,
        db_column="sucursal_piso_id",
        related_name="areas",
        blank=True,
        null=True,
    )
    area = models.CharField(max_length=100)
    tipo = models.CharField(max_length=30, blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "md_sucursal_area"
        ordering = ["tipo", "area"]

    def __str__(self):
        tipo = f"{self.tipo}: " if self.tipo else ""
        estado = "" if self.activa else " (inactiva)"
        return f"{tipo}{self.area}{estado}"


class SucursalPiso(models.Model):
    sucursal_piso_id = models.AutoField(primary_key=True)
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        db_column="sucursal_id",
        related_name="pisos",
    )
    piso = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "md_sucursal_piso"
        ordering = ["piso"]

    def __str__(self):
        estado = "" if self.activo else " (inactivo)"
        return f"{self.piso}{estado}"


class SegmentoRed(models.Model):
    segmento_red_id = models.AutoField(primary_key=True)
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        db_column="sucursal_id",
        related_name="segmentos_red",
    )
    areas = models.ManyToManyField(
        SucursalArea,
        through="SegmentoRedArea",
        through_fields=("segmento_red", "sucursal_area"),
        related_name="segmentos_red",
        blank=True,
    )
    segmento = models.CharField(max_length=50)
    segmento_nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "r_segmento_red"
        ordering = ["segmento", "segmento_nombre"]

    def __str__(self):
        estado = "" if self.activa else " (inactivo)"
        return f"{self.segmento} - {self.segmento_nombre}{estado}"

    @property
    def areas_activas(self):
        return self.areas.filter(asignaciones_segmento__activa=True)

    def asignar_areas(self, areas):
        area_ids = {
            area.pk if isinstance(area, SucursalArea) else int(area)
            for area in areas
        }
        self.asignaciones_area.exclude(sucursal_area_id__in=area_ids).update(activa=False)
        for area_id in area_ids:
            SegmentoRedArea.objects.update_or_create(
                segmento_red=self,
                sucursal_area_id=area_id,
                defaults={"activa": True},
            )


class SegmentoRedArea(models.Model):
    segmento_red_area_id = models.AutoField(primary_key=True)
    segmento_red = models.ForeignKey(
        SegmentoRed,
        on_delete=models.CASCADE,
        db_column="segmento_red_id",
        related_name="asignaciones_area",
    )
    sucursal_area = models.ForeignKey(
        SucursalArea,
        on_delete=models.CASCADE,
        db_column="sucursal_area_id",
        related_name="asignaciones_segmento",
    )
    activa = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "r_segmento_red_area"
        constraints = [
            models.UniqueConstraint(
                fields=["segmento_red", "sucursal_area"],
                name="uq_segmento_area",
            ),
        ]

    def __str__(self):
        return f"{self.segmento_red} - {self.sucursal_area}"


class Perfil(models.Model):
    perfil_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "u_perfil"

    def __str__(self):
        return self.nombre or f"Perfil {self.perfil_id}"


class Usuario(models.Model):
    usuario_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    usuario = models.CharField(max_length=50, unique=True, blank=True, null=True)
    correo = models.EmailField(max_length=150, unique=True, blank=True, null=True)
    clave = models.CharField(max_length=255, blank=True, null=True)
    perfil = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        db_column="perfil_id",
        related_name="usuarios",
        blank=True,
        null=True,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "u_usuario"

    def __str__(self):
        nombre_completo = " ".join(
            parte for parte in [self.nombre, self.apellido] if parte
        ).strip()
        return nombre_completo or self.usuario or f"Usuario {self.usuario_id}"


class UsuarioSucursal(models.Model):
    pk = models.CompositePrimaryKey("usuario_id", "sucursal_id")
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="usuario_sucursales",
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        db_column="sucursal_id",
        related_name="usuario_sucursales",
    )

    class Meta:
        managed = False
        db_table = "u_usuario_sucursal"
        unique_together = (("usuario", "sucursal"),)

    def __str__(self):
        return f"{self.usuario} - {self.sucursal}"
        
