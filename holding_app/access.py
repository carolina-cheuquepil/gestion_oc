from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import check_password, identify_hasher
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.crypto import constant_time_compare

from .models import Sucursal, Usuario, UsuarioSucursal


SESSION_USUARIO_ID = "usuario_id"
SESSION_USUARIO_NOMBRE = "usuario_nombre"
SESSION_SUCURSAL_ID = "sucursal_id"
SESSION_SUCURSAL_NOMBRE = "sucursal_nombre"
SESSION_TODAS_SUCURSALES = "todas_sucursales"


def clave_valida(usuario, clave_plana):
    clave_guardada = usuario.clave or ""
    try:
        identify_hasher(clave_guardada)
        return check_password(clave_plana, clave_guardada)
    except ValueError:
        pass
    return constant_time_compare(clave_guardada, clave_plana)


def sucursales_usuario(usuario_id):
    return Sucursal.objects.filter(
        usuario_sucursales__usuario_id=usuario_id,
        activa=True,
    ).select_related("empresa").order_by("nombre")


def sucursal_ids_usuario(usuario_id):
    return list(sucursales_usuario(usuario_id).values_list("pk", flat=True))


def usuario_autenticado(request):
    usuario_id = request.session.get(SESSION_USUARIO_ID)
    if not usuario_id:
        return None
    return Usuario.objects.filter(pk=usuario_id, activo=True).first()


def sucursal_actual_id(request):
    return request.session.get(SESSION_SUCURSAL_ID)


def sucursal_actual_ids(request):
    usuario_id = request.session.get(SESSION_USUARIO_ID)
    if not usuario_id:
        return []

    if request.session.get(SESSION_TODAS_SUCURSALES):
        return sucursal_ids_usuario(usuario_id)

    sucursal_id = sucursal_actual_id(request)
    return [sucursal_id] if sucursal_id else []


def set_sucursal_session(request, sucursal):
    request.session[SESSION_SUCURSAL_ID] = sucursal.pk
    request.session[SESSION_SUCURSAL_NOMBRE] = sucursal.nombre
    request.session.pop(SESSION_TODAS_SUCURSALES, None)


def set_todas_sucursales_session(request):
    request.session.pop(SESSION_SUCURSAL_ID, None)
    request.session[SESSION_SUCURSAL_NOMBRE] = "Todas las sucursales"
    request.session[SESSION_TODAS_SUCURSALES] = True


def clear_access_session(request):
    for key in (
        SESSION_USUARIO_ID,
        SESSION_USUARIO_NOMBRE,
        SESSION_SUCURSAL_ID,
        SESSION_SUCURSAL_NOMBRE,
        SESSION_TODAS_SUCURSALES,
    ):
        request.session.pop(key, None)


def login_sucursal_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        usuario_id = request.session.get(SESSION_USUARIO_ID)
        if not usuario_id:
            return redirect(f"{reverse('login')}?next={request.get_full_path()}")

        sucursal_ids = sucursal_ids_usuario(usuario_id)
        if not sucursal_ids:
            clear_access_session(request)
            messages.error(request, "El usuario no tiene sucursales asociadas.")
            return redirect("login")

        if request.session.get(SESSION_TODAS_SUCURSALES):
            return view_func(request, *args, **kwargs)

        if not request.session.get(SESSION_SUCURSAL_ID):
            if len(sucursal_ids) > 1:
                set_todas_sucursales_session(request)
                return view_func(request, *args, **kwargs)
            return redirect(f"{reverse('seleccionar_sucursal')}?next={request.get_full_path()}")

        if not UsuarioSucursal.objects.filter(
            usuario_id=usuario_id,
            sucursal_id=request.session[SESSION_SUCURSAL_ID],
        ).exists():
            clear_access_session(request)
            messages.error(request, "Tu sesión no tiene una sucursal válida.")
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return wrapper


class SucursalAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        return login_sucursal_required(super().dispatch)(request, *args, **kwargs)
