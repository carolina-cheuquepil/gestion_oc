#PASO 3: CRUD completo 
#Para el Frontend

from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch
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
from .models import (
    Direccion,
    Holding,
    Perfil,
    SegmentoRed,
    SegmentoRedArea,
    Sucursal,
    SucursalArea,
    SucursalPiso,
    SucursalTelefono,
    Usuario,
    UsuarioSucursal,
)
from .serializers import HoldingSerializer, PerfilSerializer, SegmentoRedSerializer, SucursalAreaSerializer, SucursalPisoSerializer, SucursalSerializer, SucursalTelefonoSerializer, UsuarioSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import DireccionForm, HoldingForm, SegmentoRedFormSet, SucursalAreaFormSet, SucursalForm, SucursalPisoFormSet, SucursalTelefonoFormSet

class HoldingViewSet(ModelViewSet):
    queryset = Holding.objects.all()
    serializer_class = HoldingSerializer


class PerfilViewSet(ModelViewSet):
    queryset = Perfil.objects.all()
    serializer_class = PerfilSerializer


class SucursalViewSet(ModelViewSet):
    queryset = Sucursal.objects.select_related("empresa", "direccion").all()
    serializer_class = SucursalSerializer


class SucursalTelefonoViewSet(ModelViewSet):
    queryset = SucursalTelefono.objects.select_related("sucursal", "sucursal__empresa", "sucursal_area").all()
    serializer_class = SucursalTelefonoSerializer


class SucursalAreaViewSet(ModelViewSet):
    queryset = SucursalArea.objects.select_related(
        "sucursal_piso",
        "sucursal_piso__sucursal",
        "sucursal_piso__sucursal__empresa",
    ).all()
    serializer_class = SucursalAreaSerializer


class SucursalPisoViewSet(ModelViewSet):
    queryset = SucursalPiso.objects.select_related("sucursal", "sucursal__empresa").all()
    serializer_class = SucursalPisoSerializer


class SegmentoRedViewSet(ModelViewSet):
    queryset = SegmentoRed.objects.select_related(
        "sucursal",
        "sucursal__empresa",
    ).prefetch_related("areas")
    serializer_class = SegmentoRedSerializer


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
    sucursales = (
        holding.sucursales
        .select_related("direccion")
        .annotate(
            total_telefonos=Count("telefonos", distinct=True),
            total_areas=Count("pisos__areas", distinct=True),
            total_pisos=Count("pisos", distinct=True),
            total_segmentos=Count("segmentos_red", distinct=True),
            total_usuarios=Count("usuario_sucursales__usuario_id", distinct=True),
        )
        .all()
    )
    return render(
        request,
        "holding_app/holding_detail.html",
        {"holding": holding, "sucursales": sucursales},
    )


@login_sucursal_required
def sucursal_detail(request, empresa_pk, pk):
    holding = get_object_or_404(Holding, pk=empresa_pk)
    sucursal = get_object_or_404(
        Sucursal.objects.select_related("empresa", "direccion").prefetch_related(
            Prefetch(
                "pisos",
                queryset=SucursalPiso.objects.prefetch_related(
                    Prefetch(
                        "areas",
                        queryset=SucursalArea.objects.prefetch_related("telefonos"),
                    ),
                ),
            ),
            Prefetch(
                "segmentos_red",
                queryset=SegmentoRed.objects.prefetch_related(
                    Prefetch(
                        "asignaciones_area",
                        queryset=SegmentoRedArea.objects.filter(
                            activa=True,
                        ).select_related(
                            "sucursal_area",
                            "sucursal_area__sucursal_piso",
                        ),
                        to_attr="asignaciones_activas",
                    ),
                ),
            ),
            Prefetch(
                "usuario_sucursales",
                queryset=UsuarioSucursal.objects.select_related("usuario", "usuario__perfil"),
            ),
        ),
        pk=pk,
        empresa=holding,
    )
    return render(
        request,
        "holding_app/sucursal_detail.html",
        {
            "holding": holding,
            "sucursal": sucursal,
            "areas": SucursalArea.objects.select_related("sucursal_piso").filter(
                sucursal_piso__sucursal=sucursal
            ),
        },
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
    sucursal_instance = sucursal or Sucursal(empresa=holding)
    sucursal_form = SucursalForm(request.POST or None, instance=sucursal)
    direccion_form = DireccionForm(request.POST or None, instance=direccion)
    direccion_existente_id = (request.POST.get("direccion_existente") or "").strip() if request.method == "POST" else ""
    direccion_existente = None
    direccion_existente_error = None
    if direccion_existente_id:
        try:
            direccion_existente = Direccion.objects.get(pk=direccion_existente_id)
        except (Direccion.DoesNotExist, ValueError):
            direccion_existente_error = "Selecciona una direccion valida."
            direccion_form.add_error(None, direccion_existente_error)

    telefono_formset = SucursalTelefonoFormSet(
        request.POST or None,
        instance=sucursal_instance,
        prefix="telefonos",
    )
    segmento_formset = SegmentoRedFormSet(
        request.POST or None,
        instance=sucursal_instance,
        prefix="segmentos",
    )
    pisos_qs = (
        SucursalPiso.objects.filter(sucursal=sucursal_instance).order_by("piso")
        if sucursal_instance.pk
        else SucursalPiso.objects.none()
    )
    area_formset = SucursalAreaFormSet(
        request.POST or None,
        queryset=(
            SucursalArea.objects.filter(sucursal_piso__sucursal=sucursal_instance)
            if sucursal_instance.pk
            else SucursalArea.objects.none()
        ),
        prefix="areas",
        form_kwargs={"pisos_queryset": pisos_qs},
    )
    piso_formset = SucursalPisoFormSet(
        request.POST or None,
        instance=sucursal_instance,
        prefix="pisos",
    )

    if (
        request.method == "POST"
        and sucursal_form.is_valid()
        and (direccion_existente is not None or direccion_form.is_valid())
        and direccion_existente_error is None
        and telefono_formset.is_valid()
        and segmento_formset.is_valid()
        and area_formset.is_valid()
        and piso_formset.is_valid()
    ):
        with transaction.atomic():
            direccion_anterior = direccion
            nueva_direccion = direccion
            if direccion_existente:
                nueva_direccion = direccion_existente
            elif direccion_form.has_address_data():
                nueva_direccion = direccion_form.save()
            else:
                nueva_direccion = None

            sucursal_obj = sucursal_form.save(commit=False)
            sucursal_obj.empresa = holding
            sucursal_obj.direccion = nueva_direccion
            sucursal_obj.save()

            telefono_formset.instance = sucursal_obj
            telefono_formset.save()
            _set_principal_unico(sucursal_obj)

            segmento_formset.instance = sucursal_obj
            segmento_formset.save()

            area_formset.save()

            piso_formset.instance = sucursal_obj
            piso_formset.save()

            if (
                direccion_anterior
                and direccion_anterior != nueva_direccion
                and not direccion_anterior.sucursales.exists()
            ):
                direccion_anterior.delete()

            return sucursal_obj, sucursal_form, direccion_form, telefono_formset, segmento_formset, area_formset, piso_formset

    return None, sucursal_form, direccion_form, telefono_formset, segmento_formset, area_formset, piso_formset


@login_sucursal_required
def sucursal_create(request, empresa_pk):
    holding = get_object_or_404(Holding, pk=empresa_pk)
    sucursal, sucursal_form, direccion_form, telefono_formset, segmento_formset, area_formset, piso_formset = _save_sucursal_forms(request, holding)
    if sucursal:
        return redirect("holding_detail", pk=holding.pk)

    direccion_existente_id = (request.POST.get("direccion_existente") or "").strip() if request.method == "POST" else ""
    return render(request, "holding_app/sucursal_form.html", {
        "holding": holding,
        "sucursal": None,
        "sucursal_form": sucursal_form,
        "direccion_form": direccion_form,
        "direcciones": Direccion.objects.order_by("ciudad", "comuna", "calle", "numero"),
        "direccion_existente_id": direccion_existente_id,
        "telefono_formset": telefono_formset,
        "segmento_formset": segmento_formset,
        "area_formset": area_formset,
        "piso_formset": piso_formset,
        "is_edit": False,
    })


@login_sucursal_required
def sucursal_update(request, empresa_pk, pk):
    holding = get_object_or_404(Holding, pk=empresa_pk)
    sucursal_obj = get_object_or_404(Sucursal, pk=pk, empresa=holding)
    sucursal, sucursal_form, direccion_form, telefono_formset, segmento_formset, area_formset, piso_formset = _save_sucursal_forms(request, holding, sucursal_obj)
    if sucursal:
        return redirect("holding_detail", pk=holding.pk)

    direccion_existente_id = (
        (request.POST.get("direccion_existente") or "").strip()
        if request.method == "POST"
        else ""
    )
    return render(request, "holding_app/sucursal_form.html", {
        "holding": holding,
        "sucursal": sucursal_obj,
        "sucursal_form": sucursal_form,
        "direccion_form": direccion_form,
        "direcciones": Direccion.objects.order_by("ciudad", "comuna", "calle", "numero"),
        "direccion_existente_id": direccion_existente_id,
        "telefono_formset": telefono_formset,
        "segmento_formset": segmento_formset,
        "area_formset": area_formset,
        "piso_formset": piso_formset,
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


def _set_principal_unico(sucursal):
    principal = (
        SucursalTelefono.objects
        .filter(sucursal=sucursal, principal=True)
        .order_by("-sucursal_telefono_id")
        .first()
    )
    if principal:
        SucursalTelefono.objects.filter(sucursal=sucursal, principal=True).exclude(pk=principal.pk).update(principal=False)

