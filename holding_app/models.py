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
        db_table = "empresa"
    
    def __str__(self):
        return self.nombre or self.razon_social


class Direccion(models.Model):
    direccion_id = models.AutoField(primary_key=True)
    calle = models.CharField(max_length=255)
    numero = models.CharField(max_length=20, null=True, blank=True)
    ciudad = models.CharField(max_length=100)
    comuna = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "direccion"

    def __str__(self):
        partes = [self.calle]
        if self.numero:
            partes.append(self.numero)
        if self.comuna:
            partes.append(self.comuna)
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
        db_table = "sucursal"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Perfil(models.Model):
    perfil_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "perfil"

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
        db_table = "usuario"

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
        db_table = "usuario_sucursal"
        unique_together = (("usuario", "sucursal"),)

    def __str__(self):
        return f"{self.usuario} - {self.sucursal}"
        
