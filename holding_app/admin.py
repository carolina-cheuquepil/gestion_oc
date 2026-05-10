from django.contrib import admin
from .models import Perfil, SegmentoRed, Sucursal, SucursalTelefono, Usuario


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("sucursal_id", "codigo_sucursal", "nombre", "empresa", "activa")
    list_filter = ("empresa", "activa")
    search_fields = ("codigo_sucursal", "nombre", "empresa__razon_social", "empresa__nombre")


@admin.register(SucursalTelefono)
class SucursalTelefonoAdmin(admin.ModelAdmin):
    list_display = ("sucursal_telefono_id", "sucursal", "tipo_telefono", "numero", "principal")
    list_filter = ("principal", "tipo_telefono")
    search_fields = ("numero", "tipo_telefono", "sucursal__nombre", "sucursal__codigo_sucursal")


@admin.register(SegmentoRed)
class SegmentoRedAdmin(admin.ModelAdmin):
    list_display = ("segmento_red_id", "sucursal", "segmento", "segmento_nombre", "activa")
    list_filter = ("activa", "sucursal__empresa")
    search_fields = ("segmento", "segmento_nombre", "sucursal__nombre", "sucursal__codigo_sucursal")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("perfil_id", "nombre")
    search_fields = ("nombre",)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario_id", "usuario", "nombre", "apellido", "correo", "perfil", "activo")
    list_filter = ("perfil", "activo")
    search_fields = ("usuario", "nombre", "apellido", "correo")
