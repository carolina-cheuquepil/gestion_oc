#PASO 3: CRUD completo 
#Para el Frontend

from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.db.models import ProtectedError
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from .access import (
    SESSION_USUARIO_ID,
    SESSION_USUARIO_NOMBRE,
    clave_valida,
    clear_access_session,
    login_sucursal_required,
    set_sucursal_session,
    set_todas_sucursales_session,
    sucursales_usuario,
)
from .models import Direccion, Holding, Perfil, Sucursal, Usuario, UsuarioSucursal
from .serializers import HoldingSerializer, PerfilSerializer, SucursalSerializer, UsuarioSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import DireccionForm, HoldingForm, SucursalForm

class HoldingViewSet(ModelViewSet):
    queryset = Holding.objects.all()
    serializer_class = HoldingSerializer


class PerfilViewSet(ModelViewSet):
    queryset = Perfil.objects.all()
    serializer_class = PerfilSerializer


class SucursalViewSet(ModelViewSet):
    queryset = Sucursal.objects.select_related("empresa", "direccion").all()
    serializer_class = SucursalSerializer


class UsuarioViewSet(ModelViewSet):
    queryset = Usuario.objects.select_related("perfil").all()
    serializer_class = UsuarioSerializer


def holding_buscar_codigo(request):
    holding_id = request.GET.get("id", "").strip()
    codigo = request.GET.get("codigo", "").strip()
    try:
        if holding_id and holding_id.isdigit():
            h = Holding.objects.get(pk=int(holding_id))
        elif codigo and codigo.isdigit():
            h = Holding.objects.get(codigo_empresa=int(codigo))
        else:
            return JsonResponse({"error": "Parámetro inválido"}, status=400)
        return JsonResponse({
            "id": h.pk,
            "codigo_empresa": h.codigo_empresa,
            "razon_social": h.razon_social or h.nombre or "",
        })
    except Holding.DoesNotExist:
        return JsonResponse({"error": "No encontrado"}, status=404)


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or reverse("compras_ui")
    error = None

    if request.method == "POST":
        username = (request.POST.get("usuario") or "").strip()
        clave = request.POST.get("clave") or ""

        usuario = Usuario.objects.filter(usuario=username, activo=True).first()
        if usuario and clave_valida(usuario, clave):
            clear_access_session(request)
            request.session[SESSION_USUARIO_ID] = usuario.pk
            request.session[SESSION_USUARIO_NOMBRE] = str(usuario)

            sucursales = list(sucursales_usuario(usuario.pk))
            if len(sucursales) == 1:
                set_sucursal_session(request, sucursales[0])
            elif len(sucursales) > 1:
                set_todas_sucursales_session(request)
            else:
                clear_access_session(request)
                error = "El usuario no tiene sucursales asociadas."
                return render(request, "holding_app/login.html", {"error": error, "next": next_url})

            return redirect(next_url)
        else:
            error = "Usuario o clave inválidos."

    return render(request, "holding_app/login.html", {"error": error, "next": next_url})


def logout_view(request):
    clear_access_session(request)
    request.session.flush()
    return redirect("login")


def seleccionar_sucursal(request):
    usuario_id = request.session.get(SESSION_USUARIO_ID)
    if not usuario_id:
        return redirect("login")

    next_url = request.GET.get("next") or request.POST.get("next") or request.session.get("post_login_next") or reverse("compras_ui")
    sucursales = list(sucursales_usuario(usuario_id))

    if len(sucursales) == 1:
        set_sucursal_session(request, sucursales[0])
        return redirect(next_url)

    if request.method == "POST":
        sucursal_id = request.POST.get("sucursal")
        if sucursal_id == "todas" and len(sucursales) > 1:
            set_todas_sucursales_session(request)
            request.session.pop("post_login_next", None)
            return redirect(next_url)

        sucursal = next((s for s in sucursales if str(s.pk) == str(sucursal_id)), None)
        if sucursal:
            set_sucursal_session(request, sucursal)
            request.session.pop("post_login_next", None)
            return redirect(next_url)
        messages.error(request, "Selecciona una sucursal válida.")

    return render(
        request,
        "holding_app/seleccionar_sucursal.html",
        {"sucursales": sucursales, "next": next_url},
    )


@login_sucursal_required
def holding_frontend(request):
    holdings = Holding.objects.prefetch_related("sucursales").all()
    codigo = request.GET.get("codigo", "").strip()
    if codigo:
        holdings = holdings.filter(codigo_empresa=codigo) if codigo.isdigit() else holdings.none()
    return render(request, "holding_app/holding_list.html", {"holdings": holdings, "codigo": codigo})

@login_sucursal_required
def holding_create(request):
    if request.method == "POST":
        form = HoldingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("holdings_ui")
    else:
        form = HoldingForm()

    return render(request, "holding_app/holding_form.html", {"form": form})

@login_sucursal_required
def holding_update(request, pk):
    holding = get_object_or_404(Holding, pk=pk)

    if request.method == "POST":
        form = HoldingForm(request.POST, instance=holding)
        if form.is_valid():
            form.save()
            return redirect("holdings_ui")
    else:
        form = HoldingForm(instance=holding)

    return render(
        request,
        "holding_app/holding_form.html",
        {"form": form, "holding": holding, "is_edit": True},
    )


@login_sucursal_required
def holding_detail(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    usuario_unico_sucursal = (
        UsuarioSucursal.objects
        .select_related("usuario")
        .filter(usuario__activo=True)
        .annotate(
            total_sucursales_activas=Count(
                "usuario__usuario_sucursales__sucursal_id",
                filter=Q(usuario__usuario_sucursales__sucursal__activa=True),
                distinct=True,
            )
        )
        .filter(total_sucursales_activas=1)
    )
    sucursales = (
        holding.sucursales
        .select_related("direccion")
        .prefetch_related(
            Prefetch(
                "usuario_sucursales",
                queryset=usuario_unico_sucursal,
                to_attr="usuarios_unicos",
            )
        )
        .all()
    )
    return render(
        request,
        "holding_app/holding_detail.html",
        {"holding": holding, "sucursales": sucursales},
    )


@login_sucursal_required
def holding_delete(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    error = None

    if request.method == "POST":
        try:
            holding.delete()
            return redirect("holdings_ui")
        except (ProtectedError, IntegrityError):
            error = "No se puede eliminar la empresa porque tiene documentos o registros asociados."

    return render(
        request,
        "holding_app/holding_confirm_delete.html",
        {"holding": holding, "error": error},
    )


def _save_sucursal_forms(request, holding, sucursal=None):
    direccion = sucursal.direccion if sucursal and sucursal.direccion_id else None
    sucursal_form = SucursalForm(request.POST or None, instance=sucursal)
    direccion_form = DireccionForm(request.POST or None, instance=direccion)

    if request.method == "POST" and sucursal_form.is_valid() and direccion_form.is_valid():
        with transaction.atomic():
            direccion_anterior = direccion
            nueva_direccion = direccion
            if direccion_form.has_address_data():
                nueva_direccion = direccion_form.save()
            else:
                nueva_direccion = None

            sucursal_obj = sucursal_form.save(commit=False)
            sucursal_obj.empresa = holding
            sucursal_obj.direccion = nueva_direccion
            sucursal_obj.save()

            if direccion_anterior and not nueva_direccion and not direccion_anterior.sucursales.exists():
                direccion_anterior.delete()

            return sucursal_obj, sucursal_form, direccion_form

    return None, sucursal_form, direccion_form


@login_sucursal_required
def sucursal_create(request, empresa_pk):
    holding = get_object_or_404(Holding, pk=empresa_pk)
    sucursal, sucursal_form, direccion_form = _save_sucursal_forms(request, holding)
    if sucursal:
        return redirect("holding_detail", pk=holding.pk)

    return render(request, "holding_app/sucursal_form.html", {
        "holding": holding,
        "sucursal": None,
        "sucursal_form": sucursal_form,
        "direccion_form": direccion_form,
        "is_edit": False,
    })


@login_sucursal_required
def sucursal_update(request, empresa_pk, pk):
    holding = get_object_or_404(Holding, pk=empresa_pk)
    sucursal_obj = get_object_or_404(Sucursal, pk=pk, empresa=holding)
    sucursal, sucursal_form, direccion_form = _save_sucursal_forms(request, holding, sucursal_obj)
    if sucursal:
        return redirect("holding_detail", pk=holding.pk)

    return render(request, "holding_app/sucursal_form.html", {
        "holding": holding,
        "sucursal": sucursal_obj,
        "sucursal_form": sucursal_form,
        "direccion_form": direccion_form,
        "is_edit": True,
    })


@login_sucursal_required
def sucursal_delete(request, empresa_pk, pk):
    holding = get_object_or_404(Holding, pk=empresa_pk)
    sucursal = get_object_or_404(Sucursal, pk=pk, empresa=holding)
    error = None

    if request.method == "POST":
        try:
            direccion = sucursal.direccion
            sucursal.delete()
            if direccion and not direccion.sucursales.exists():
                direccion.delete()
            return redirect("holding_detail", pk=holding.pk)
        except (ProtectedError, IntegrityError):
            error = "No se puede eliminar la sucursal porque tiene compras, activos u otros registros asociados."

    return render(request, "holding_app/sucursal_confirm_delete.html", {
        "holding": holding,
        "sucursal": sucursal,
        "error": error,
    })

