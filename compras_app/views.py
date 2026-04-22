#PASO 3° BD: CRUD completo
#FrontEnd C: Paso 3
from django.shortcuts import render, redirect, get_object_or_404
from .models import Compra, HistorialCompra, CompraItem, FacturaIntercompany, FacturaIntercompanyItem, TipoDocumento, EstadoDocumento, TipoOC, Moneda, ProyectoInformatica
from proveedores_app.models import ProveedorProducto, ProveedorProductoPrecio
from .serializers import CompraSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import CompraForm, CompraItemFormSet, FacturaIntercompanyForm, FacturaIntercompanyItemFormSet, CotizacionUploadForm, ProyectoForm, FacturaProveedorForm
from activos_app.models import RecepcionCompraItem
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.db.models import Max
from decimal import Decimal
from django.db.models import Prefetch
from holding_app.models import Holding
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import mimetypes


class CompraViewSet(ModelViewSet):
    queryset = Compra.objects.all()
    serializer_class = CompraSerializer


IVA_PCT = Decimal("0.19")
RETENCION_PCT = Decimal("0.1375")

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

#----------------- Compras IT ---------------
def compras_frontend(request):
    oc_enviada_sub = HistorialCompra.objects.filter(
        compra=OuterRef("pk"),
        tipo_documento__codigo="EMAIL",
    )
    compras = Compra.objects.select_related(
        "tipo_documento", "estado_documento", "proveedor", "razon_social"
    ).annotate(oc_enviada=Exists(oc_enviada_sub))
    return render(request, "compras_app/compras_list.html", {"compras": compras})

def compra_detail(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related(
            "tipo_documento", "estado_documento", "proveedor", "razon_social", "moneda"
        ).prefetch_related(
            "historial",
            "items__producto",
        ),
        pk=pk,
    )
    return render(request, "compras_app/compra_detail.html", {"compra": compra})


@transaction.atomic
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
                    HistorialCompra.objects.create(
                        compra=compra,
                        fecha_evento=timezone.now(),
                        fecha_documento=fecha_cot,
                        tipo_documento=td_cot,
                        estado_documento=estado_cot,
                        folio=folio_cot,
                        archivo=archivo_cot,
                    )

            HistorialCompra.objects.create(
                compra=compra,
                fecha_evento=timezone.now(),
                fecha_documento=compra.fecha_emision,
                tipo_documento=compra.tipo_documento,
                estado_documento=compra.estado_documento,
                folio=compra.folio,
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

class CompraUpdateView(UpdateView):
    model = Compra
    form_class = CompraForm
    template_name = "compras_app/compra_form.html"
    pk_url_kwarg = "pk"
    context_object_name = "compra"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        compra = self.object

        if "formset" not in ctx:
            if self.request.method == "POST":
                proveedor_id = self.request.POST.get("proveedor") or compra.proveedor_id
                proveedor_id = int(proveedor_id) if proveedor_id else None
                ctx["formset"] = CompraItemFormSet(
                    self.request.POST,
                    instance=compra,
                    form_kwargs={"proveedor": proveedor_id},
                )
            else:
                ctx["formset"] = CompraItemFormSet(
                    instance=compra,
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

            folio_cot = form.cleaned_data.get("folio_cotizacion") or ""
            fecha_cot = form.cleaned_data.get("fecha_cotizacion")
            if folio_cot or fecha_cot:
                td_cot = TipoDocumento.objects.filter(codigo="COT").first()
                if td_cot:
                    HistorialCompra.objects.create(
                        compra=compra,
                        fecha_evento=timezone.now(),
                        fecha_documento=fecha_cot,
                        tipo_documento=td_cot,
                        estado_documento=compra.estado_documento,
                        folio=folio_cot,
                    )

            if header_changed or items_changed:
                HistorialCompra.objects.create(
                    compra=compra,
                    fecha_evento=timezone.now(),
                    fecha_documento=compra.fecha_emision,
                    tipo_documento=compra.tipo_documento,
                    estado_documento=compra.estado_documento,
                    folio=compra.folio,
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
def facturas_ic_frontend(request):
    facturas = FacturaIntercompany.objects.all()
    return render(
        request,
        "compras_app/facturas_ic_list.html",
        {"facturas": facturas},
    )

@transaction.atomic
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

    form = FacturaIntercompanyForm(initial={"recargo_porcentaje": Decimal("5.00")})
    formset = FacturaIntercompanyItemFormSet(form_kwargs={"compra_origen": None})

    return render(request, "compras_app/factura_ic_form.html", {
        "form": form,
        "formset": formset,
        "is_edit": False,
    })

def factura_ic_detail(request, pk):
    factura = get_object_or_404(
        FacturaIntercompany.objects.select_related(
            "empresa_emisora",
            "empresa_receptora",
            "compra_origen",
            "moneda",
        ).prefetch_related(
            "items",
            "items__compra_item__producto",
        ),
        pk=pk,
    )
    return render(request, "compras_app/factura_ic_detail.html", {"factura": factura})


class FacturaICUpdateView(UpdateView):
    model = FacturaIntercompany
    form_class = FacturaIntercompanyForm
    template_name = "compras_app/factura_ic_form.html"
    pk_url_kwarg = "pk"
    context_object_name = "factura"

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
    subject = f"Solicitud autorización OC N° {compra.folio}"
    body = render_to_string("compras_app/oc_autorizacion.html", {"compra": compra})

    email = EmailMessage(
        subject=subject,
        body=body,
        to=["carolina.cheuquepil@dimarsa.cl"],
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

    email.send()

    td_email, _ = TipoDocumento.objects.get_or_create(
        codigo="EMAIL",
        defaults={"nombre": "Correo"}
    )
    estado_enviado = EstadoDocumento.objects.get(nombre="Enviado")

    compra.historial.create(
        fecha_evento=timezone.now(),
        fecha_documento=timezone.now().date(),
        tipo_documento=td_email,
        estado_documento=estado_enviado,
        folio=compra.folio
    )


def enviar_oc(request, pk):
    if request.method != "POST":
        return redirect("compra_detail", pk=pk)

    compra = get_object_or_404(Compra, pk=pk)
    estado_espera = EstadoDocumento.objects.get(nombre="En espera")
    compra.estado = estado_espera
    compra.save()

    enviar_correo_oc(compra)

    return redirect("compra_detail", pk=pk)


def aprobar_oc(request, pk):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    compra = get_object_or_404(Compra, pk=pk)
    fecha_str = request.POST.get("fecha_aprobacion", "").strip()

    try:
        from datetime import date as date_cls
        fecha = date_cls.fromisoformat(fecha_str) if fecha_str else timezone.now().date()
    except ValueError:
        return JsonResponse({"ok": False, "error": "Fecha inválida."}, status=400)

    estado_aprobado, _ = EstadoDocumento.objects.get_or_create(nombre="Aprobado")

    HistorialCompra.objects.create(
        compra=compra,
        fecha_evento=timezone.now(),
        fecha_documento=fecha,
        tipo_documento=compra.tipo_documento,
        estado_documento=estado_aprobado,
        folio=compra.folio,
    )

    compra.estado_documento = estado_aprobado
    compra.save(update_fields=["estado_documento_id"])

    return JsonResponse({"ok": True})


def cotizacion_upload(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
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
def registrar_factura_recepcion(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "razon_social", "moneda", "tipo_documento", "estado_documento")
                      .prefetch_related(
                          "items__producto__tipo_producto",
                          "items__recepciones",
                      ),
        pk=pk,
    )
    items = list(compra.items.all())

    if request.method == "POST":
        factura_form = FacturaProveedorForm(request.POST, request.FILES)

        if factura_form.is_valid():
            folio_factura = (factura_form.cleaned_data.get("folio_factura") or "").strip()
            fecha_factura = factura_form.cleaned_data.get("fecha_factura")
            archivo_factura = request.FILES.get("archivo_factura")

            if folio_factura or archivo_factura:
                td_fact, _ = TipoDocumento.objects.get_or_create(
                    codigo="FACT",
                    defaults={"nombre": "Factura Proveedor"},
                )
                estado_recibido, _ = EstadoDocumento.objects.get_or_create(nombre="Recibido")
                HistorialCompra.objects.create(
                    compra=compra,
                    fecha_evento=timezone.now(),
                    fecha_documento=fecha_factura,
                    tipo_documento=td_fact,
                    estado_documento=estado_recibido,
                    folio=folio_factura or None,
                    archivo=archivo_factura,
                )

            nuevas_recepciones = []
            for item in items:
                qty_str = request.POST.get(f"recepcion_cantidad_{item.compra_item_id}", "").strip()
                obs_str = request.POST.get(f"recepcion_obs_{item.compra_item_id}", "").strip()
                if qty_str:
                    try:
                        qty = Decimal(qty_str)
                        if qty > 0:
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
                HistorialCompra.objects.create(
                    compra=compra,
                    fecha_evento=timezone.now(),
                    fecha_documento=timezone.now().date(),
                    tipo_documento=td_recep,
                    estado_documento=estado_recibido,
                    folio=compra.folio,
                )

                # Si algún ítem recibido es Activo Fijo, redirigir a registro de activos
                recp_af = [
                    r for r in nuevas_recepciones
                    if r.compra_item.producto_id
                    and "activo" in r.compra_item.producto.tipo_producto.nombre.lower()
                ]
                if recp_af:
                    ids_param = ",".join(str(r.recepcion_compra_item_id) for r in recp_af)
                    from django.urls import reverse
                    url = reverse("activos_registrar", kwargs={"compra_pk": compra.pk})
                    return redirect(f"{url}?recp={ids_param}")

            return redirect("compra_detail", pk=compra.pk)
    else:
        factura_form = FacturaProveedorForm()

    items_info = []
    for item in items:
        recepciones = list(item.recepciones.all())
        total_recibido = sum(r.cantidad_recibida for r in recepciones)
        items_info.append({
            "item": item,
            "total_recibido": total_recibido,
            "pendiente": item.cantidad - total_recibido,
            "recepciones": recepciones,
        })

    facturas_registradas = list(compra.historial.filter(tipo_documento__codigo="FACT"))

    return render(request, "compras_app/factura_recepcion_form.html", {
        "compra": compra,
        "factura_form": factura_form,
        "items_info": items_info,
        "facturas_registradas": facturas_registradas,
    })


# ----------- Proyectos TI ------------

def proyectos_list(request):
    proyectos = ProyectoInformatica.objects.all()
    return render(request, "compras_app/proyectos_list.html", {"proyectos": proyectos})


def proyecto_create(request):
    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("proyectos_list")
    else:
        form = ProyectoForm()
    return render(request, "compras_app/proyecto_form.html", {"form": form, "is_edit": False})


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


def proyecto_delete(request, pk):
    if request.method == "POST":
        proyecto = get_object_or_404(ProyectoInformatica, pk=pk)
        proyecto.delete()
    return redirect("proyectos_list")
