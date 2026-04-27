from django.contrib import admin
from .models import Perfil, Sucursal, Usuario


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("sucursal_id", "codigo_sucursal", "nombre", "empresa", "activa")
    list_filter = ("empresa", "activa")
    search_fields = ("codigo_sucursal", "nombre", "empresa__razon_social", "empresa__nombre")

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("perfil_id", "nombre")
    search_fields = ("nombre",)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario_id", "usuario", "nombre", "apellido", "correo", "perfil", "activo")
    list_filter = ("perfil", "activo")
    search_fields = ("usuario", "nombre", "apellido", "correo")
