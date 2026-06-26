#PASO 3° BD: CRUD completo
#FrontEnd C: Paso 3
from django.shortcuts import render, redirect, get_object_or_404
from .models import Compra, CorreoDestinatario, HistorialCompra, CompraItem, FacturaIntercompany, FacturaIntercompanyItem, TipoDocumento, EstadoDocumento, TipoOC, Moneda, ProyectoInformatica, ProyectoInformaticaCosto
from proveedores_app.models import ProveedorProducto, ProveedorProductoPrecio
from .serializers import CompraSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import CompraForm, CompraItemFormSet, CorreoDestinatarioForm, FacturaIntercompanyForm, FacturaIntercompanyItemFormSet, CotizacionUploadForm, ProyectoForm, FacturaProveedorForm, ProyectoServicioCostoForm
from activos_app.models import ActivoFijo, RecepcionCompraItem
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.conf import settings
from django.contrib import messages
from django.db import OperationalError, ProgrammingError, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Count, Exists, OuterRef, Sum
from django.utils import timezone
from django.db.models import Max
from decimal import Decimal
from django.db.models import Prefetch
from holding_app.models import Holding
from holding_app.access import (
    login_sucursal_required,
    SucursalAccessMixin,
)
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import mimetypes
import smtplib
import calendar


class CompraViewSet(ModelViewSet):
    queryset = Compra.objects.all()
    serializer_class = CompraSerializer


IVA_PCT = Decimal("0.19")
RETENCION_PCT = Decimal("0.1375")
TIPO_PRODUCTO_SERVICIO_ID = 3


def _sumar_un_mes(fecha):
    year = fecha.year + (1 if fecha.month == 12 else 0)
    month = 1 if fecha.month == 12 else fecha.month + 1
    last_day = calendar.monthrange(year, month)[1]
    return fecha.replace(year=year, month=month, day=min(fecha.day, last_day))


def _destinatarios_correo(tipo, fallback=None):
    try:
        destinatarios = list(
            CorreoDestinatario.objects
            .filter(tipo=tipo, activo=True)
            .values_list("email", flat=True)
        )
    except (OperationalError, ProgrammingError):
        destinatarios = []
    if destinatarios:
        return destinatarios
    return list(fallback or [])


def _item_requiere_recepcion(item):
    if not item.producto_id:
        return True
    return item.producto.tipo_producto_id != TIPO_PRODUCTO_SERVICIO_ID


def _recalcular_totales_compra(compra):
    total_neto = Decimal("0.00")
    for item in compra.items.all():
        subtotal = (item.cantidad * item.precio_unitario
                    * (1 - item.descuento_porcentaje / 100))
        total_neto += subtotal.quantize(Decimal("0.01"))

    tipo = compra.tipo_oc
    iva = (total_neto * IVA_PCT).quantize(Decimal("0.01")) if tipo.afecta_iva else Decimal("0.00")
    retencion = (total_neto * RETENCION_PCT).quantize(Decimal("0.01")) if tipo.requiere_retencion else Decimal("0.00")

    compra.total_neto = total_neto
    compra.total_iva = iva
    compra.total = (total_neto + iva - retencion).quantize(Decimal("0.01"))
    compra.save(update_fields=["total_neto", "total_iva", "total"])


def _sincronizar_compra_con_historial(compra, historial=None, save=True):
    historial = historial or (
        compra.historial
        .select_related("tipo_documento", "estado_documento")
        .order_by("-fecha_evento", "-historial_compra_id")
        .first()
    )
    if not historial:
        return compra

    changed = []
    if compra.tipo_documento_id != historial.tipo_documento_id:
        compra.tipo_documento = historial.tipo_documento
        changed.append("tipo_documento_id")
    if compra.estado_documento_id != historial.estado_documento_id:
        compra.estado_documento = historial.estado_documento
        changed.append("estado_documento_id")
    if compra.folio != historial.folio:
        compra.folio = historial.folio
        changed.append("folio")

    if save and changed:
        compra.save(update_fields=changed)

    return compra


def _crear_historial_documento(
    compra,
    tipo_documento,
    estado_documento,
    folio=None,
    fecha_documento=None,
    archivo=None,
    factura_total_neto_clp=None,
    factura_total_iva_clp=None,
    factura_total_clp=None,
):
    """
    Una compra es el expediente principal; cotizacion, OC, factura, recepcion,
    correos y aprobaciones quedan como documentos/eventos de su historial.
    """
    historial = HistorialCompra.objects.create(
        compra=compra,
        fecha_evento=timezone.now(),
        fecha_documento=fecha_documento,
        tipo_documento=tipo_documento,
        estado_documento=estado_documento,
        folio=folio,
        archivo=archivo,
        factura_total_neto_clp=factura_total_neto_clp,
        factura_total_iva_clp=factura_total_iva_clp,
        factura_total_clp=factura_total_clp,
    )
    _sincronizar_compra_con_historial(compra, historial=historial)
    return historial


def _historial_documento_existe(compra, tipo_documento, folio=None, fecha_documento=None, archivo=None):
    qs = HistorialCompra.objects.filter(compra=compra, tipo_documento=tipo_documento)
    if folio:
        qs = qs.filter(folio=folio)
    if fecha_documento:
        qs = qs.filter(fecha_documento=fecha_documento)
    if archivo:
        qs = qs.filter(archivo=archivo)
    return qs.exists()


@login_sucursal_required
def correos_destinatarios_list(request):
    correos = CorreoDestinatario.objects.all()
    return render(
        request,
        "compras_app/correos_destinatarios_list.html",
        {"correos": correos},
    )


@login_sucursal_required
def correo_destinatario_create(request):
    if request.method == "POST":
        form = CorreoDestinatarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Correo agregado.")
            return redirect("correos_destinatarios_list")
    else:
        form = CorreoDestinatarioForm()
    return render(
        request,
        "compras_app/correo_destinatario_form.html",
        {"form": form, "is_edit": False},
    )


@login_sucursal_required
def correo_destinatario_update(request, pk):
    correo = get_object_or_404(CorreoDestinatario, pk=pk)
    if request.method == "POST":
        form = CorreoDestinatarioForm(request.POST, instance=correo)
        if form.is_valid():
            form.save()
            messages.success(request, "Correo actualizado.")
            return redirect("correos_destinatarios_list")
    else:
        form = CorreoDestinatarioForm(instance=correo)
    return render(
        request,
        "compras_app/correo_destinatario_form.html",
        {"form": form, "is_edit": True, "correo": correo},
    )


@login_sucursal_required
def correo_destinatario_delete(request, pk):
    correo = get_object_or_404(CorreoDestinatario, pk=pk)
    if request.method == "POST":
        correo.delete()
        messages.success(request, "Correo eliminado.")
        return redirect("correos_destinatarios_list")
    return render(
        request,
        "compras_app/correo_destinatario_confirm_delete.html",
        {"correo": correo},
    )

#----------------- Compras IT ---------------
@login_sucursal_required
def compras_frontend(request):
    oc_enviada_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="EMAIL",
    )
    factura_registrada_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="FACT",
    )
    oc_aprobada_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="OC",
        estado_documento__nombre="Aprobado",
    )
    contabilidad_ingresada_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="EMAIL",
        estado_documento__nombre__iexact="Cobrado",
    )
    cobranza_pendiente_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="EMAIL",
        estado_documento__nombre__iexact="En espera",
    )
    contabilidad_legacy_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="CONT",
    )
    pago_registrado_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento_id=5,
        estado_documento_id=7,
    )
    compras = Compra.objects.select_related(
        "tipo_documento", "estado_documento", "proveedor", "razon_social"
    ).prefetch_related(
        Prefetch(
            "historial",
            queryset=HistorialCompra.objects.select_related(
                "tipo_documento", "estado_documento"
            ).order_by("-fecha_evento"),
            to_attr="historial_ordenado",
        ),
    ).distinct().annotate(
        oc_enviada=Exists(oc_enviada_sub),
        factura_registrada=Exists(factura_registrada_sub),
        oc_aprobada=Exists(oc_aprobada_sub),
        contabilidad_ingresada=Exists(contabilidad_ingresada_sub),
        cobranza_pendiente=Exists(cobranza_pendiente_sub),
        contabilidad_legacy_ingresada=Exists(contabilidad_legacy_sub),
        pago_registrado=Exists(pago_registrado_sub),
    )

    compras_por_proveedor = []
    compras_list = sorted(
        list(compras),
        key=lambda compra: (str(compra.proveedor or "").lower(), compra.fecha_emision, compra.compra_id),
    )
    for compra in compras_list:
        compra.ultimo_historial = (
            compra.historial_ordenado[0]
            if getattr(compra, "historial_ordenado", None)
            else None
        )
        _sincronizar_compra_con_historial(compra, historial=compra.ultimo_historial, save=False)
        compra.contabilidad_ingresada = compra.contabilidad_ingresada or compra.contabilidad_legacy_ingresada
        compra.cobranza_pendiente_historial = next(
            (
                h for h in getattr(compra, "historial_ordenado", [])
                if h.tipo_documento.codigo == "EMAIL"
                and h.estado_documento.nombre.lower() == "en espera"
            ),
            None,
        )
        if not compras_por_proveedor or compras_por_proveedor[-1]["proveedor"] != compra.proveedor:
            compras_por_proveedor.append({
                "proveedor": compra.proveedor,
                "compras": [],
            })
        compras_por_proveedor[-1]["compras"].append(compra)

    return render(
        request,
        "compras_app/compras_list.html",
        {
            "compras": compras,
            "compras_por_proveedor": compras_por_proveedor,
        },
    )


@login_sucursal_required
def compra_detail(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related(
            "tipo_documento", "estado_documento", "proveedor", "razon_social", "moneda"
        ).prefetch_related(
            "historial",
            Prefetch(
                "items",
                queryset=CompraItem.objects.select_related("producto"),
            ),
        ),
        pk=pk,
    )
    _sincronizar_compra_con_historial(compra)
    return render(request, "compras_app/compra_detail.html", {"compra": compra})


@transaction.atomic
@login_sucursal_required
def compra_create(request):
    if request.method == "POST":
        form = CompraForm(request.POST, request.FILES)

        form_ok = form.is_valid()

        proveedor_id = request.POST.get("proveedor") or None
        proveedor_id = int(proveedor_id) if proveedor_id else None

        compra_tmp = form.save(commit=False) if form_ok else None

        formset = CompraItemFormSet(
            request.POST,
            instance=compra_tmp,
            form_kwargs={"proveedor": proveedor_id},
        )

        formset_ok = formset.is_valid()

        if form_ok and formset_ok:
            td_oc = TipoDocumento.objects.filter(codigo="OC").first()
            if td_oc and compra_tmp:
                compra_tmp.tipo_documento = td_oc
            compra = form.save()
            oc_tipo_documento = compra.tipo_documento
            oc_estado_documento = compra.estado_documento
            oc_folio = compra.folio
            oc_fecha_emision = compra.fecha_emision

            folio_cot = form.cleaned_data.get("folio_cotizacion") or ""
            fecha_cot = form.cleaned_data.get("fecha_cotizacion")
            archivo_cot = request.FILES.get("cotizacion_archivo")
            if folio_cot or fecha_cot or archivo_cot:
                td_cot = TipoDocumento.objects.filter(codigo="COT").first()
                if td_cot:
                    estado_cot = (
                        EstadoDocumento.objects.filter(nombre="Recibido").first()
                        if archivo_cot else compra.estado_documento
                    )
                    _crear_historial_documento(
                        compra=compra,
                        tipo_documento=td_cot,
                        estado_documento=estado_cot,
                        folio=folio_cot,
                        fecha_documento=fecha_cot,
                        archivo=archivo_cot,
                    )

            _crear_historial_documento(
                compra=compra,
                tipo_documento=oc_tipo_documento,
                estado_documento=oc_estado_documento,
                folio=oc_folio,
                fecha_documento=oc_fecha_emision,
            )

            formset.instance = compra
            items = formset.save(commit=False)

            last = (
                CompraItem.objects.filter(compra=compra)
                .aggregate(m=Max("nro_linea"))["m"] or 0
            )
            n = last + 1

            for it in items:
                if not it.pk:
                    it.nro_linea = n
                    n += 1

                it.compra = compra
                it.save()

                if it.producto_id:
                    pp, _ = ProveedorProducto.objects.get_or_create(
                        proveedor_id=compra.proveedor_id,
                        producto_id=it.producto_id,
                        defaults={},
                    )

                    precio_actual = it.precio_unitario or Decimal("0.00")
                    moneda_codigo = compra.moneda.codigo

                    ultimo = (
                        ProveedorProductoPrecio.objects
                        .filter(proveedor_producto_id=pp.proveedor_producto_id)
                        .order_by("-proveedor_producto_precio_id")
                        .first()
                    )

                    if (not ultimo) or (ultimo.precio_neto != precio_actual) or (ultimo.moneda != moneda_codigo):
                        ProveedorProductoPrecio.objects.create(
                            proveedor_producto_id=pp.proveedor_producto_id,
                            precio_neto=precio_actual,
                            moneda=moneda_codigo,
                        )

            for obj in formset.deleted_objects:
                obj.delete()

            formset.save_m2m()
            _recalcular_totales_compra(compra)

            if request.POST.get("guardar_y_enviar_oc") == "1":
                if archivo_cot and (compra.folio or "").strip():
                    enviado, error = solicitar_aprobacion_oc(compra)
                    if enviado:
                        messages.success(request, "Compra guardada y correo de OC enviado.")
                    else:
                        messages.warning(request, f"Compra guardada, pero no se envio el correo de OC. {error}")
                else:
                    messages.warning(
                        request,
                        "Compra guardada, pero no se envio el correo de OC. Debe ingresar folio OC y adjuntar cotizacion PDF.",
                    )
                return redirect("compras_ui")

            return redirect("compra_update", pk=compra.pk)

        print("FORM errors:", form.errors)
        print("FORMSET errors:", formset.errors)
        print("FORMSET non form errors:", formset.non_form_errors())

        return render(request, "compras_app/compra_form.html", {
            "form": form,
            "formset": formset,
            "is_edit": False,
            "tipos_oc": list(TipoOC.objects.values("tipo_oc_id", "afecta_iva", "requiere_retencion")),
            "monedas": list(Moneda.objects.values("moneda_id", "codigo")),
        })

    form = CompraForm()
    formset = CompraItemFormSet(form_kwargs={"proveedor": None})

    return render(request, "compras_app/compra_form.html", {
        "form": form,
        "formset": formset,
        "is_edit": False,
        "tipos_oc": list(TipoOC.objects.values("tipo_oc_id", "afecta_iva", "requiere_retencion")),
        "monedas": list(Moneda.objects.values("moneda_id", "codigo")),
    })

class CompraUpdateView(SucursalAccessMixin, UpdateView):
    model = Compra
    form_class = CompraForm
    template_name = "compras_app/compra_form.html"
    pk_url_kwarg = "pk"
    context_object_name = "compra"

    def get_queryset(self):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        compra = self.object

        if "formset" not in ctx:
            item_queryset = CompraItem.objects.all()
            if self.request.method == "POST":
                proveedor_id = self.request.POST.get("proveedor") or compra.proveedor_id
                proveedor_id = int(proveedor_id) if proveedor_id else None
                ctx["formset"] = CompraItemFormSet(
                    self.request.POST,
                    instance=compra,
                    queryset=item_queryset,
                    form_kwargs={"proveedor": proveedor_id},
                )
            else:
                ctx["formset"] = CompraItemFormSet(
                    instance=compra,
                    queryset=item_queryset,
                    form_kwargs={"proveedor": compra.proveedor_id},
                )

        ctx["is_edit"] = True
        ctx["tipos_oc"] = list(TipoOC.objects.values("tipo_oc_id", "afecta_iva", "requiere_retencion"))
        ctx["monedas"] = list(Moneda.objects.values("moneda_id", "codigo"))
        ctx["tiene_cotizacion"] = (
            compra.historial
            .filter(tipo_documento__codigo="COT", archivo__isnull=False)
            .exclude(archivo="")
            .exists()
        )
        return ctx

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form = self.get_form()
        formset = self.get_context_data(form=form)["formset"]

        form_ok = form.is_valid()
        formset_ok = formset.is_valid()

        if form_ok and formset_ok:
            header_changed = form.has_changed()
            items_changed = formset.has_changed()

            td_oc = TipoDocumento.objects.filter(codigo="OC").first()
            compra = form.save(commit=False)
            if td_oc:
                compra.tipo_documento = td_oc
            compra.save()
            form.save_m2m()
            oc_tipo_documento = compra.tipo_documento
            oc_estado_documento = compra.estado_documento
            oc_folio = compra.folio
            oc_fecha_emision = compra.fecha_emision

            folio_cot = form.cleaned_data.get("folio_cotizacion") or ""
            fecha_cot = form.cleaned_data.get("fecha_cotizacion")
            if folio_cot or fecha_cot:
                td_cot = TipoDocumento.objects.filter(codigo="COT").first()
                if td_cot and not _historial_documento_existe(compra, td_cot, folio_cot, fecha_cot):
                    _crear_historial_documento(
                        compra=compra,
                        tipo_documento=td_cot,
                        estado_documento=compra.estado_documento,
                        folio=folio_cot,
                        fecha_documento=fecha_cot,
                    )

            if header_changed or items_changed:
                _crear_historial_documento(
                    compra=compra,
                    tipo_documento=oc_tipo_documento,
                    estado_documento=oc_estado_documento,
                    folio=oc_folio,
                    fecha_documento=oc_fecha_emision,
                )

            items = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            last = (CompraItem.objects.filter(compra=compra)
                    .aggregate(m=Max("nro_linea"))["m"] or 0)
            n = last + 1

            for it in items:
                if not it.pk:
                    it.nro_linea = n
                    n += 1

                it.compra = compra
                it.save()

                if it.producto_id:
                    pp, _ = ProveedorProducto.objects.get_or_create(
                        proveedor_id=compra.proveedor_id,
                        producto_id=it.producto_id,
                        defaults={},
                    )

                    precio_actual = it.precio_unitario or Decimal("0.00")
                    moneda_codigo = compra.moneda.codigo

                    ultimo = (ProveedorProductoPrecio.objects
                              .filter(proveedor_producto_id=pp.proveedor_producto_id)
                              .order_by("-proveedor_producto_precio_id")
                              .first())

                    if (not ultimo) or (ultimo.precio_neto != precio_actual) or (ultimo.moneda != moneda_codigo):
                        ProveedorProductoPrecio.objects.create(
                            proveedor_producto_id=pp.proveedor_producto_id,
                            precio_neto=precio_actual,
                            moneda=moneda_codigo,
                        )

            formset.save_m2m()
            _recalcular_totales_compra(compra)

            return redirect("compra_detail", pk=compra.pk)

        print("FORM errors:", form.errors)
        print("FORM changed_data:", form.changed_data)
        print("FORMSET errors:", formset.errors)
        print("FORMSET non_form_errors:", formset.non_form_errors())

        return self.render_to_response(self.get_context_data(form=form, formset=formset))

compra_update = CompraUpdateView.as_view()

# ----------- Distribución interna ------------
@login_sucursal_required
def facturas_ic_frontend(request):
    facturas = FacturaIntercompany.objects.all().distinct()
    return render(
        request,
        "compras_app/facturas_ic_list.html",
        {"facturas": facturas},
    )

@transaction.atomic
@login_sucursal_required
def factura_ic_create(request):
    if request.method == "POST":
        form = FacturaIntercompanyForm(request.POST)
        form_ok = form.is_valid()

        compra_id = request.POST.get("compra_origen") or None
        compra_id = int(compra_id) if compra_id else None

        factura_tmp = form.save(commit=False) if form_ok else None

        formset = FacturaIntercompanyItemFormSet(
            request.POST,
            instance=factura_tmp,
            form_kwargs={"compra_origen": compra_id},
        )
        formset_ok = formset.is_valid()

        if form_ok and formset_ok:
            factura = form.save()

            formset.instance = factura
            items = formset.save(commit=False)

            for it in items:
                it.factura_ic = factura
                it.save()

            for obj in formset.deleted_objects:
                obj.delete()

            formset.save_m2m()

            return redirect("factura_ic_detail", pk=factura.pk)

        return render(request, "compras_app/factura_ic_form.html", {
            "form": form,
            "formset": formset,
            "is_edit": False,
        })

    form = FacturaIntercompanyForm(
        initial={"recargo_porcentaje": Decimal("5.00")},
    )
    formset = FacturaIntercompanyItemFormSet(
        form_kwargs={"compra_origen": None},
    )

    return render(request, "compras_app/factura_ic_form.html", {
        "form": form,
        "formset": formset,
        "is_edit": False,
    })

@login_sucursal_required
def factura_ic_detail(request, pk):
    factura = get_object_or_404(
        FacturaIntercompany.objects.select_related(
            "empresa_emisora",
            "empresa_receptora",
            "compra_origen",
            "moneda",
        ).prefetch_related(
            Prefetch(
                "items",
                queryset=FacturaIntercompanyItem.objects.select_related("compra_item__producto"),
            ),
        ).distinct(),
        pk=pk,
    )
    return render(request, "compras_app/factura_ic_detail.html", {"factura": factura})


class FacturaICUpdateView(SucursalAccessMixin, UpdateView):
    model = FacturaIntercompany
    form_class = FacturaIntercompanyForm
    template_name = "compras_app/factura_ic_form.html"
    pk_url_kwarg = "pk"
    context_object_name = "factura"

    def get_queryset(self):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        factura = self.object

        if "formset" not in ctx:
            if self.request.method == "POST":
                compra_id = self.request.POST.get("compra_origen") or factura.compra_origen_id
                compra_id = int(compra_id) if compra_id else None

                ctx["formset"] = FacturaIntercompanyItemFormSet(
                    self.request.POST,
                    instance=factura,
                    form_kwargs={"compra_origen": compra_id},
                )
            else:
                ctx["formset"] = FacturaIntercompanyItemFormSet(
                    instance=factura,
                    form_kwargs={"compra_origen": factura.compra_origen_id},
                )

        ctx["is_edit"] = True
        return ctx

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form = self.get_form()
        formset = self.get_context_data(form=form)["formset"]

        form_ok = form.is_valid()
        formset_ok = formset.is_valid()

        if form_ok and formset_ok:
            factura = form.save()

            items = formset.save(commit=False)

            for it in items:
                it.factura_ic = factura
                it.save()

            for obj in formset.deleted_objects:
                obj.delete()

            formset.save_m2m()

            factura.recalcular_totales(save=True)

            return redirect("factura_ic_detail", pk=factura.pk)

        return self.render_to_response(self.get_context_data(form=form, formset=formset))


factura_ic_update = FacturaICUpdateView.as_view()


def holding_por_codigo(request):
    codigo = request.GET.get("codigo")
    holding = Holding.objects.filter(codigo_empresa=codigo).first()
    if not holding:
        return JsonResponse({"ok": False})
    return JsonResponse({"ok": True, "id": holding.pk})


def enviar_correo_oc(compra):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return False, (
            "No se pudo enviar el correo de OC porque faltan las variables "
            "EMAIL_HOST_USER y/o EMAIL_HOST_PASSWORD."
        )

    subject = f"Solicitud autorización OC N° {compra.folio}"
    body = render_to_string("compras_app/oc_autorizacion.html", {"compra": compra})
    destinatarios = _destinatarios_correo(
        CorreoDestinatario.TIPO_AUTORIZACION_OC,
        ["carolina.cheuquepil@dimarsa.cl"],
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        to=destinatarios,
    )
    email.content_subtype = "html"

    cot = (
        compra.historial
        .filter(tipo_documento__codigo="COT", archivo__isnull=False)
        .exclude(archivo="")
        .last()
    )

    if cot and cot.archivo:
        filename = cot.archivo.name.split("/")[-1]
        ctype, _ = mimetypes.guess_type(filename)
        with cot.archivo.open("rb") as f:
            email.attach(filename, f.read(), ctype or "application/pdf")

    try:
        email.send()
    except (smtplib.SMTPException, OSError) as exc:
        return False, f"No se pudo enviar el correo de OC: {exc}"

    td_email, _ = TipoDocumento.objects.get_or_create(
        codigo="EMAIL",
        defaults={"nombre": "Correo"}
    )
    estado_enviado = EstadoDocumento.objects.get(nombre="Enviado")

    _crear_historial_documento(
        compra=compra,
        tipo_documento=td_email,
        estado_documento=estado_enviado,
        folio=compra.folio,
        fecha_documento=timezone.now().date(),
    )

    return True, ""


def enviar_correo_cobranza_factura(compra, factura, fecha_contabilidad):
    fecha_emision_factura = factura.fecha_documento or compra.fecha_emision
    fecha_envio_cobranza = _sumar_un_mes(fecha_emision_factura)
    fecha_despacho_cobranza = timezone.localdate()
    if fecha_despacho_cobranza < fecha_envio_cobranza:
        td_correo = (
            TipoDocumento.objects.filter(pk=4).first()
            or TipoDocumento.objects.filter(codigo="EMAIL").first()
            or TipoDocumento.objects.create(codigo="EMAIL", nombre="Correo")
        )
        estado_espera = (
            EstadoDocumento.objects.filter(nombre__iexact="En espera").first()
            or EstadoDocumento.objects.create(nombre="En espera")
        )
        if not HistorialCompra.objects.filter(
            compra=compra,
            tipo_documento=td_correo,
            estado_documento=estado_espera,
            folio=factura.folio or compra.folio,
            fecha_documento=fecha_envio_cobranza,
        ).exists():
            _crear_historial_documento(
                compra=compra,
                tipo_documento=td_correo,
                estado_documento=estado_espera,
                folio=factura.folio or compra.folio,
                fecha_documento=fecha_envio_cobranza,
            )
        return False, (
            "El correo de cobranza quedo en espera hasta "
            f"{fecha_envio_cobranza.strftime('%d-%m-%Y')}."
        )

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return False, (
            "No se pudo enviar el correo de cobranza porque faltan las variables "
            "EMAIL_HOST_USER y/o EMAIL_HOST_PASSWORD."
        )

    destinatarios = (
        _destinatarios_correo(
            CorreoDestinatario.TIPO_COBRANZA_CONTABILIDAD,
            settings.COBRANZA_CONTABILIDAD_EMAILS,
        )
        + _destinatarios_correo(
            CorreoDestinatario.TIPO_COBRANZA_TESORERIA,
            settings.COBRANZA_TESORERIA_EMAILS,
        )
    )
    if not destinatarios:
        return False, (
            "No se pudo enviar el correo de cobranza porque faltan destinatarios. "
            "Configura COBRANZA_CONTABILIDAD_EMAILS y/o COBRANZA_TESORERIA_EMAILS."
        )

    dias_desde_emision = (fecha_despacho_cobranza - fecha_emision_factura).days
    cobranza_vencida = fecha_despacho_cobranza > fecha_envio_cobranza
    moneda_cobranza = "CLP" if factura.factura_total_clp is not None else compra.moneda
    total_neto_cobranza = (
        factura.factura_total_neto_clp
        if factura.factura_total_neto_clp is not None else compra.total_neto
    )
    total_iva_cobranza = (
        factura.factura_total_iva_clp
        if factura.factura_total_iva_clp is not None else compra.total_iva
    )
    total_cobranza = (
        factura.factura_total_clp
        if factura.factura_total_clp is not None else compra.total
    )
    subject = f"Cobranza factura {factura.folio or compra.folio or compra.pk} - {compra.proveedor}"
    if cobranza_vencida:
        subject = f"URGENTE - {subject}"
    body = render_to_string(
        "compras_app/cobranza_factura.html",
        {
            "compra": compra,
            "factura": factura,
            "fecha_emision_factura": fecha_emision_factura,
            "fecha_envio_cobranza": fecha_envio_cobranza,
            "fecha_contabilidad": fecha_contabilidad,
            "fecha_despacho_cobranza": fecha_despacho_cobranza,
            "dias_desde_emision": dias_desde_emision,
            "cobranza_vencida": cobranza_vencida,
            "moneda_cobranza": moneda_cobranza,
            "total_neto_cobranza": total_neto_cobranza,
            "total_iva_cobranza": total_iva_cobranza,
            "total_cobranza": total_cobranza,
        },
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        to=destinatarios,
    )
    email.content_subtype = "html"
    if cobranza_vencida:
        email.extra_headers = {
            "Importance": "High",
            "Priority": "urgent",
            "X-Priority": "1",
        }

    if factura.archivo:
        filename = factura.archivo.name.split("/")[-1]
        ctype, _ = mimetypes.guess_type(filename)
        with factura.archivo.open("rb") as f:
            email.attach(filename, f.read(), ctype or "application/pdf")

    try:
        email.send()
    except (smtplib.SMTPException, OSError) as exc:
        return False, f"No se pudo enviar el correo de cobranza: {exc}"

    td_correo = (
        TipoDocumento.objects.filter(pk=4).first()
        or TipoDocumento.objects.filter(codigo="EMAIL").first()
        or TipoDocumento.objects.create(codigo="EMAIL", nombre="Correo")
    )
    estado_cobrado = (
        EstadoDocumento.objects.filter(pk=9).first()
        or EstadoDocumento.objects.filter(nombre__iexact="Cobrado").first()
        or EstadoDocumento.objects.create(nombre="Cobrado")
    )

    _crear_historial_documento(
        compra=compra,
        tipo_documento=td_correo,
        estado_documento=estado_cobrado,
        folio=factura.folio or compra.folio,
        fecha_documento=timezone.now().date(),
    )

    return True, ""


def solicitar_aprobacion_oc(compra):
    td_oc = TipoDocumento.objects.filter(codigo="OC").first() or compra.tipo_documento
    folio_oc = compra.folio
    enviado, error = enviar_correo_oc(compra)
    if not enviado:
        return False, error

    estado_espera = EstadoDocumento.objects.get(nombre="En espera")
    if not HistorialCompra.objects.filter(
        compra=compra,
        tipo_documento=td_oc,
        estado_documento=estado_espera,
    ).exists():
        _crear_historial_documento(
            compra=compra,
            tipo_documento=td_oc,
            estado_documento=estado_espera,
            folio=folio_oc,
            fecha_documento=timezone.now().date(),
        )
    return True, ""


@login_sucursal_required
def enviar_oc(request, pk):
    if request.method != "POST":
        return redirect("compras_ui")

    compra = get_object_or_404(
        Compra.objects.all(),
        pk=pk,
    )
    enviado, error = solicitar_aprobacion_oc(compra)
    if enviado:
        messages.success(request, "Correo de OC enviado.")
    else:
        messages.warning(request, error)

    return redirect("compras_ui")


@login_sucursal_required
def aprobar_oc(request, pk):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    compra = get_object_or_404(
        Compra.objects.all(),
        pk=pk,
    )
    _sincronizar_compra_con_historial(compra)
    if HistorialCompra.objects.filter(
        compra=compra,
        tipo_documento__codigo="OC",
        estado_documento__nombre="Aprobado",
    ).exists():
        return JsonResponse({"ok": False, "error": "Esta OC ya esta aprobada."}, status=400)

    fecha_str = request.POST.get("fecha_aprobacion", "").strip()

    try:
        from datetime import date as date_cls
        fecha = date_cls.fromisoformat(fecha_str) if fecha_str else timezone.now().date()
    except ValueError:
        return JsonResponse({"ok": False, "error": "Fecha inválida."}, status=400)

    estado_aprobado, _ = EstadoDocumento.objects.get_or_create(nombre="Aprobado")

    _crear_historial_documento(
        compra=compra,
        tipo_documento=TipoDocumento.objects.filter(codigo="OC").first() or compra.tipo_documento,
        estado_documento=estado_aprobado,
        folio=compra.folio,
        fecha_documento=fecha,
    )

    return JsonResponse({"ok": True})


@transaction.atomic
@login_sucursal_required
def registrar_ingreso_contabilidad(request, pk):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    compra = get_object_or_404(
        Compra.objects.prefetch_related("historial"),
        pk=pk,
    )
    _sincronizar_compra_con_historial(compra)

    fecha_firma_str = request.POST.get("fecha_firma", "").strip()
    fecha_contabilidad_str = request.POST.get("fecha_contabilidad", "").strip()
    firmante = request.POST.get("firmante", "").strip()
    firmantes_validos = {
        "Sub Gerente De Informatica": "Sub Gerente De Informatica",
        "Jefe de Soporte Informatico": "Jefe de Soporte Informatico",
    }

    if firmante not in firmantes_validos:
        return JsonResponse({"ok": False, "error": "Debes seleccionar quien firma la factura."}, status=400)

    try:
        from datetime import date as date_cls
        fecha_firma = date_cls.fromisoformat(fecha_firma_str)
        fecha_contabilidad = date_cls.fromisoformat(fecha_contabilidad_str)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Debes ingresar fechas validas."}, status=400)

    if fecha_contabilidad < fecha_firma:
        return JsonResponse(
            {"ok": False, "error": "La fecha de ingreso a contabilidad no puede ser anterior a la firma."},
            status=400,
        )
    factura = (
        HistorialCompra.objects
        .filter(compra=compra, tipo_documento__codigo="FACT")
        .order_by("-fecha_evento", "-historial_compra_id")
        .first()
    )
    if not factura:
        return JsonResponse({"ok": False, "error": "Primero debes registrar la factura recibida."}, status=400)
    if not factura.folio:
        return JsonResponse({"ok": False, "error": "La factura recibida debe tener folio antes de enviarla a Contabilidad."}, status=400)

    if not HistorialCompra.objects.filter(
        compra=compra,
        tipo_documento__codigo="OC",
        estado_documento__nombre="Aprobado",
    ).exists():
        return JsonResponse({"ok": False, "error": "La OC debe estar aprobada antes de enviar a Contabilidad."}, status=400)

    if HistorialCompra.objects.filter(
        compra=compra,
        tipo_documento__codigo="EMAIL",
        estado_documento__nombre__iexact="Cobrado",
    ).exists():
        return JsonResponse({"ok": False, "error": "Esta compra ya fue ingresada a contabilidad."}, status=400)

    archivo_firma = request.FILES.get("archivo_firma")
    if not archivo_firma:
        return JsonResponse({"ok": False, "error": "Debes subir la factura firmada."}, status=400)

    td_factura = TipoDocumento.objects.filter(pk=3).first()
    if not td_factura:
        return JsonResponse({"ok": False, "error": "No existe el tipo_documento 3 Factura."}, status=400)

    estado_firmado = EstadoDocumento.objects.filter(pk=11).first()
    if not estado_firmado:
        return JsonResponse({"ok": False, "error": "No existe el estado_documento 11 Firmado."}, status=400)

    estado_enviado_contabilidad, _ = EstadoDocumento.objects.get_or_create(nombre="Enviado a contabilidad")

    _crear_historial_documento(
        compra=compra,
        tipo_documento=td_factura,
        estado_documento=estado_firmado,
        folio=factura.folio,
        fecha_documento=fecha_firma,
        archivo=archivo_firma,
        factura_total_neto_clp=factura.factura_total_neto_clp,
        factura_total_iva_clp=factura.factura_total_iva_clp,
        factura_total_clp=factura.factura_total_clp,
    )
    factura_enviada = _crear_historial_documento(
        compra=compra,
        tipo_documento=factura.tipo_documento,
        estado_documento=estado_enviado_contabilidad,
        folio=factura.folio,
        fecha_documento=factura.fecha_documento,
        archivo=archivo_firma,
        factura_total_neto_clp=factura.factura_total_neto_clp,
        factura_total_iva_clp=factura.factura_total_iva_clp,
        factura_total_clp=factura.factura_total_clp,
    )
    enviado, error = enviar_correo_cobranza_factura(compra, factura_enviada, fecha_contabilidad)
    if not enviado:
        if error.startswith("El correo de cobranza quedo en espera"):
            return JsonResponse({"ok": True, "warning": error, "reload": True})
        return JsonResponse({"ok": True, "warning": error})

    return JsonResponse({"ok": True})


@transaction.atomic
@login_sucursal_required
def registrar_pago(request, pk):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    compra = get_object_or_404(
        Compra.objects.prefetch_related("historial"),
        pk=pk,
    )
    _sincronizar_compra_con_historial(compra)

    fecha_pago_str = request.POST.get("fecha_pago", "").strip()
    try:
        from datetime import date as date_cls
        fecha_pago = date_cls.fromisoformat(fecha_pago_str)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Debes ingresar una fecha de pago valida."}, status=400)

    contabilidad_registrada = HistorialCompra.objects.filter(
        compra=compra,
        tipo_documento__codigo="EMAIL",
        estado_documento__nombre__iexact="Cobrado",
    ).exists() or HistorialCompra.objects.filter(compra=compra, tipo_documento__codigo="CONT").exists()
    if not contabilidad_registrada:
        return JsonResponse({"ok": False, "error": "Primero debes enviar la factura a Contabilidad."}, status=400)

    if HistorialCompra.objects.filter(compra=compra, tipo_documento_id=5, estado_documento_id=7).exists():
        return JsonResponse({"ok": False, "error": "Esta compra ya tiene un pago registrado."}, status=400)

    td_pago = TipoDocumento.objects.filter(pk=5).first()
    if not td_pago:
        return JsonResponse({"ok": False, "error": "No existe el tipo_documento 5 Pago."}, status=400)

    estado_pagado = EstadoDocumento.objects.filter(pk=7).first()
    if not estado_pagado:
        return JsonResponse({"ok": False, "error": "No existe el estado_documento 7 Pagado."}, status=400)

    factura = (
        HistorialCompra.objects
        .filter(compra=compra, tipo_documento__codigo="FACT")
        .order_by("-fecha_evento", "-historial_compra_id")
        .first()
    )

    _crear_historial_documento(
        compra=compra,
        tipo_documento=td_pago,
        estado_documento=estado_pagado,
        folio=(factura.folio if factura else None) or compra.folio,
        fecha_documento=fecha_pago,
        archivo=request.FILES.get("archivo"),
    )

    return JsonResponse({"ok": True})


@login_sucursal_required
def cotizacion_upload(request, pk):
    compra = get_object_or_404(
        Compra.objects.all(),
        pk=pk,
    )
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        archivo = request.FILES.get("archivo")
        if not archivo:
            if is_ajax:
                return JsonResponse({"ok": False, "errors": {"archivo": [{"message": "Debes seleccionar un archivo."}]}}, status=400)
            return redirect("compra_update", pk=compra.pk)

        td_cot = TipoDocumento.objects.get(codigo="COT")
        estado_recibido = EstadoDocumento.objects.get(nombre="Recibido")

        cot_ref = HistorialCompra.objects.filter(
            compra=compra,
            tipo_documento=td_cot,
        ).order_by("-fecha_evento").first()

        h = HistorialCompra(
            compra=compra,
            tipo_documento=td_cot,
            estado_documento=estado_recibido,
            fecha_evento=timezone.now(),
            folio=cot_ref.folio if cot_ref else None,
            fecha_documento=cot_ref.fecha_documento if cot_ref else None,
            archivo=archivo,
        )
        h.save()

        if is_ajax:
            return JsonResponse({"ok": True})
        return redirect("compra_detail", pk=compra.pk)
    else:
        form = CotizacionUploadForm()

    return render(request, "compras_app/cotizacion_upload.html", {
        "compra": compra,
        "form": form
    })


# ----------- Factura Proveedor + Recepción ------------

@transaction.atomic
@login_sucursal_required
def registrar_factura_recepcion(request, pk):
    return _registrar_factura_recepcion(request, pk, solo_recepcion=False)


@transaction.atomic
@login_sucursal_required
def registrar_recepcion_productos(request, pk):
    return _registrar_factura_recepcion(request, pk, solo_recepcion=True)


def _registrar_factura_recepcion(request, pk, solo_recepcion=False):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "razon_social", "moneda", "tipo_documento", "estado_documento")
                      .prefetch_related(
                          Prefetch(
                              "items",
                              queryset=CompraItem.objects.select_related("producto__tipo_producto").prefetch_related("recepciones"),
                          ),
                      ),
        pk=pk,
    )
    items = list(compra.items.all())
    requiere_montos_clp = (compra.moneda.codigo or "").upper() != "CLP"

    if request.method == "POST":
        factura_form = FacturaProveedorForm(
            request.POST,
            request.FILES,
            requiere_montos_clp=requiere_montos_clp,
        )

        if factura_form.is_valid():
            fecha_factura = factura_form.cleaned_data.get("fecha_factura")
            folio_factura = factura_form.cleaned_data.get("folio_factura")

            if fecha_factura:
                td_fact, _ = TipoDocumento.objects.get_or_create(
                    codigo="FACT",
                    defaults={"nombre": "Factura Proveedor"},
                )
                estado_recibido, _ = EstadoDocumento.objects.get_or_create(nombre="Recibido")
                _crear_historial_documento(
                    compra=compra,
                    tipo_documento=td_fact,
                    estado_documento=estado_recibido,
                    folio=folio_factura,
                    fecha_documento=fecha_factura,
                    factura_total_neto_clp=factura_form.cleaned_data.get("factura_total_neto_clp"),
                    factura_total_iva_clp=factura_form.cleaned_data.get("factura_total_iva_clp"),
                    factura_total_clp=factura_form.cleaned_data.get("factura_total_clp"),
                )

            nuevas_recepciones = []
            for item in items:
                if not _item_requiere_recepcion(item):
                    continue
                qty_str = request.POST.get(f"recepcion_cantidad_{item.compra_item_id}", "").strip()
                obs_str = request.POST.get(f"recepcion_obs_{item.compra_item_id}", "").strip()
                if qty_str:
                    try:
                        qty = Decimal(qty_str)
                        if qty != qty.to_integral_value():
                            continue
                        total_recibido = sum(
                            (r.cantidad_recibida or Decimal("0.000"))
                            for r in item.recepciones.all()
                        )
                        pendiente = (item.cantidad or Decimal("0.000")) - total_recibido
                        if qty > 0 and qty <= pendiente:
                            rec = RecepcionCompraItem.objects.create(
                                compra_item=item,
                                cantidad_recibida=qty,
                                observacion=obs_str or None,
                            )
                            nuevas_recepciones.append(rec)
                    except Exception:
                        pass

            if nuevas_recepciones:
                td_recep, _ = TipoDocumento.objects.get_or_create(
                    codigo="RECEP",
                    defaults={"nombre": "Recepción"},
                )
                estado_recibido, _ = EstadoDocumento.objects.get_or_create(nombre="Recibido")
                _crear_historial_documento(
                    compra=compra,
                    tipo_documento=td_recep,
                    estado_documento=estado_recibido,
                    folio=compra.folio,
                    fecha_documento=timezone.now().date(),
                )

                # Si algún ítem recibido es Activo Fijo, redirigir a registro de activos
                recp_af = [
                    r for r in nuevas_recepciones
                    if r.compra_item.producto_id
                    and "activo" in r.compra_item.producto.tipo_producto.nombre.lower()
                ]
                if recp_af:
                    from activos_app.views import registrar_recepciones_en_custodia_informatica

                    registrar_recepciones_en_custodia_informatica(recp_af)
                    return redirect("activos_informatica_list")

            if solo_recepcion:
                return redirect("recepcion_productos_list")
            return redirect("compra_detail", pk=compra.pk)
    else:
        factura_form = FacturaProveedorForm(requiere_montos_clp=requiere_montos_clp)

    items_info = []
    for item in items:
        recepciones = list(item.recepciones.all())
        total_recibido = sum(r.cantidad_recibida for r in recepciones)
        requiere_recepcion = _item_requiere_recepcion(item)
        items_info.append({
            "item": item,
            "total_recibido": total_recibido,
            "pendiente": item.cantidad - total_recibido if requiere_recepcion else Decimal("0.000"),
            "recepciones": recepciones,
            "requiere_recepcion": requiere_recepcion,
        })

    facturas_registradas = list(compra.historial.filter(tipo_documento__codigo="FACT"))

    return render(request, "compras_app/factura_recepcion_form.html", {
        "compra": compra,
        "factura_form": factura_form,
        "items_info": items_info,
        "facturas_registradas": facturas_registradas,
        "solo_recepcion": solo_recepcion,
        "requiere_montos_clp": requiere_montos_clp,
    })


@login_sucursal_required
def recepcion_productos_list(request):
    compras = (
        Compra.objects.select_related("proveedor", "razon_social", "moneda")
        .filter(historial__tipo_documento__codigo="FACT")
        .prefetch_related(
            Prefetch(
                "historial",
                queryset=HistorialCompra.objects.filter(tipo_documento__codigo="FACT"),
                to_attr="facturas_registradas",
            ),
            Prefetch(
                "items",
                queryset=CompraItem.objects.select_related("producto__tipo_producto").prefetch_related("recepciones"),
                to_attr="items_con_recepciones",
            ),
        )
        .distinct()
        .order_by("-compra_id")
    )

    pendientes = []
    for compra in compras:
        total_oc = Decimal("0.000")
        total_recibido = Decimal("0.000")
        lineas_pendientes = 0

        for item in getattr(compra, "items_con_recepciones", []):
            if not _item_requiere_recepcion(item):
                continue
            cantidad = item.cantidad or Decimal("0.000")
            recibido = sum((r.cantidad_recibida or Decimal("0.000")) for r in item.recepciones.all())
            pendiente = cantidad - recibido
            total_oc += cantidad
            total_recibido += recibido
            if pendiente > 0:
                lineas_pendientes += 1

        total_pendiente = total_oc - total_recibido
        if total_pendiente > 0:
            pendientes.append({
                "compra": compra,
                "facturas": getattr(compra, "facturas_registradas", []),
                "total_oc": total_oc,
                "total_recibido": total_recibido,
                "total_pendiente": total_pendiente,
                "lineas_pendientes": lineas_pendientes,
            })

    return render(request, "compras_app/recepcion_productos_list.html", {
        "pendientes": pendientes,
    })


# ----------- Proyectos TI ------------

@login_sucursal_required
def proyectos_list(request):
    proyectos = ProyectoInformatica.objects.annotate(
        total_activos=Count("activos_fijos", distinct=True),
        total_servicios=Count("costos_servicio", distinct=True),
    )
    for proyecto in proyectos:
        proyecto.valor_activos = proyecto.activos_fijos.aggregate(total=Sum("valor"))["total"] or Decimal("0.00")
        proyecto.valor_servicios = proyecto.costos_servicio.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        proyecto.valor_total = proyecto.valor_activos + proyecto.valor_servicios
    return render(request, "compras_app/proyectos_list.html", {"proyectos": proyectos})


@login_sucursal_required
def proyecto_activos(request, pk):
    proyecto = get_object_or_404(
        ProyectoInformatica.objects.annotate(
            total_activos=Count("activos_fijos", distinct=True),
            total_servicios=Count("costos_servicio", distinct=True),
        ),
        pk=pk,
    )
    proyecto.valor_activos = proyecto.activos_fijos.aggregate(total=Sum("valor"))["total"] or Decimal("0.00")
    proyecto.valor_servicios = proyecto.costos_servicio.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    proyecto.valor_total = proyecto.valor_activos + proyecto.valor_servicios

    if request.method == "POST":
        form = ProyectoServicioCostoForm(request.POST)
        if form.is_valid():
            costo = form.save(commit=False)
            costo.proyecto = proyecto
            costo.save()
            messages.success(request, "Servicio agregado como costo del proyecto.")
            return redirect("proyecto_activos", pk=proyecto.pk)
    else:
        form = ProyectoServicioCostoForm()

    activos = (
        ActivoFijo.objects
        .select_related(
            "producto",
            "sucursal__empresa",
            "recepcion_compra_item__compra_item__compra",
        )
        .filter(proyecto_informatica=proyecto)
        .order_by("nombre_activo")
    )
    costos_servicio = (
        ProyectoInformaticaCosto.objects
        .select_related("compra_item__compra__moneda", "compra_item__producto")
        .filter(proyecto=proyecto)
    )
    return render(
        request,
        "compras_app/proyecto_activos.html",
        {
            "proyecto": proyecto,
            "activos": activos,
            "costos_servicio": costos_servicio,
            "servicio_form": form,
        },
    )


@login_sucursal_required
def proyecto_costo_delete(request, pk, costo_pk):
    if request.method == "POST":
        costo = get_object_or_404(ProyectoInformaticaCosto, pk=costo_pk, proyecto_id=pk)
        costo.delete()
        messages.success(request, "Costo de servicio quitado del proyecto.")
    return redirect("proyecto_activos", pk=pk)


@login_sucursal_required
def proyecto_create(request):
    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("proyectos_list")
    else:
        form = ProyectoForm()
    return render(request, "compras_app/proyecto_form.html", {"form": form, "is_edit": False})


@login_sucursal_required
def proyecto_update(request, pk):
    proyecto = get_object_or_404(ProyectoInformatica, pk=pk)
    if request.method == "POST":
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            return redirect("proyectos_list")
    else:
        form = ProyectoForm(instance=proyecto)
    return render(request, "compras_app/proyecto_form.html", {"form": form, "is_edit": True, "proyecto": proyecto})


@login_sucursal_required
def proyecto_delete(request, pk):
    if request.method == "POST":
        proyecto = get_object_or_404(ProyectoInformatica, pk=pk)
        proyecto.delete()
    return redirect("proyectos_list")
