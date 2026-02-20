#PASO 3° BD: CRUD completo 
#FrontEnd C: Paso 3
from django.shortcuts import render, redirect, get_object_or_404
from .models import Proveedor, Producto, Compra, HistorialCompra, ProveedorProducto, CompraItem, ProveedorProductoPrecio, FacturaIntercompany, FacturaIntercompanyItem, TipoDocumento, HistorialCompra, EstadoDocumento
from .serializers import ProveedorSerializer, ProductoSerializer, CompraSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import ProveedorForm, ProductoForm, CompraForm, CompraItemFormSet, ProveedorProductoForm, FacturaIntercompanyForm, FacturaIntercompanyItemFormSet, CotizacionUploadForm
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.db.models import Max
from decimal import Decimal
from django.db.models import Prefetch
from holding_app.models import Holding
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import mimetypes



#----------------- CRUD Completo ---------------
class ProveedorViewSet(ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer

class ProductoViewSet(ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CompraViewSet(ModelViewSet):
    queryset =  Compra.objects.all()
    serializer_class = CompraSerializer

#----------------- Proveedores ---------------
def proveedores_frontend(request):
    proveedores = Proveedor.objects.all()
    return render(request, "compras_app/proveedores_list.html", {"proveedores": proveedores})

def proveedor_create(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("proveedores_ui")
    else:
        form = ProveedorForm()

    return render(request, "compras_app/proveedor_form.html", {"form": form})

def proveedor_update(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            return redirect("proveedores_ui")
    else:
        form = ProveedorForm(instance=proveedor)

    return render(
        request,
        "compras_app/proveedor_form.html",
        {"form": form, "proveedor": proveedor, "is_edit": True},
    )

#----------------- Productos ---------------
def productos_frontend(request):
    productos = ProveedorProducto.objects.select_related(
    'producto',
    'proveedor')

    return render(request, "compras_app/productos_list.html", {"productos": productos})

def producto_create(request):
    proveedor_id = request.GET.get("proveedor_id")
    proveedor = None

    if proveedor_id:
        proveedor = get_object_or_404(Proveedor, pk=proveedor_id)

    if request.method == "POST":
        form = ProductoForm(request.POST)

        # Si vienes desde proveedor, forzamos ese proveedor
        if proveedor:
            rel_form = ProveedorProductoForm(
                request.POST,
                initial={"proveedor": proveedor}
            )
        else:
            rel_form = ProveedorProductoForm(request.POST)

        if form.is_valid() and rel_form.is_valid():
            with transaction.atomic():
                producto = form.save()
                rel = rel_form.save(commit=False)
                rel.producto = producto

                if proveedor:  # fuerza el proveedor
                    rel.proveedor = proveedor

                rel.save()
            return redirect("productos_ui")
    else:
        form = ProductoForm()
        rel_form = ProveedorProductoForm(
            initial={"proveedor": proveedor} if proveedor else None
        )

    # opcional: para que el template sepa si viene “desde proveedor”
    return render(request, "compras_app/producto_form.html", {
        "form": form,
        "rel_form": rel_form,
        "is_edit": False,
        "proveedor_fijado": bool(proveedor),
        "proveedor": proveedor,
    })

def producto_update(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    # si tu producto puede tener solo 1 proveedor:
    relacion, _ = ProveedorProducto.objects.get_or_create(
        producto=producto,
        defaults={"uom_compra": "UN"}  # opcional
    )

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        rel_form = ProveedorProductoForm(request.POST, instance=relacion)

        if form.is_valid() and rel_form.is_valid():
            with transaction.atomic():
                form.save()
                rel_form.save()
            return redirect("productos_ui")
    else:
        form = ProductoForm(instance=producto)
        rel_form = ProveedorProductoForm(instance=relacion)

    return render(request, "compras_app/producto_form.html", {
        "form": form,
        "rel_form": rel_form,
        "producto": producto,
        "is_edit": True
    })

#----------------- Compras IT ---------------
def compras_frontend(request):
    compras = Compra.objects.all()
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
        form = CompraForm(request.POST)

        # 1) validar form UNA sola vez
        form_ok = form.is_valid()

        # 2) proveedor_id (int o None)
        proveedor_id = request.POST.get("proveedor") or None
        proveedor_id = int(proveedor_id) if proveedor_id else None

        # 3) instancia temporal (solo si el encabezado es válido)
        compra_tmp = form.save(commit=False) if form_ok else None

        # 4) formset con filtro por proveedor
        formset = CompraItemFormSet(
            request.POST,
            instance=compra_tmp,
            form_kwargs={"proveedor": proveedor_id},
        )

        formset_ok = formset.is_valid()

        if form_ok and formset_ok:
            # Guardar encabezado
            compra = form.save()

            # Historial (creación)
            HistorialCompra.objects.create(
                compra=compra,
                fecha_evento=timezone.now(),
                fecha_documento=compra.fecha_emision,
                tipo_documento=compra.tipo_documento,
                estado_documento=compra.estado_documento,
                folio=compra.folio,
            )

            # Guardar ítems
            formset.instance = compra
            items = formset.save(commit=False)

            # nro_linea automático (por seguridad)
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

                # Historial de precio (solo si hay producto)
                if it.producto_id:
                    pp, _ = ProveedorProducto.objects.get_or_create(
                        proveedor_id=compra.proveedor_id,
                        producto_id=it.producto_id,
                        defaults={"uom_compra": None},
                    )

                    precio_actual = it.precio_unitario or Decimal("0.00")
                    moneda = compra.moneda

                    ultimo = (
                        ProveedorProductoPrecio.objects
                        .filter(proveedor_producto_id=pp.proveedor_producto_id)
                        .order_by("-proveedor_producto_precio_id")
                        .first()
                    )

                    if (not ultimo) or (ultimo.precio_neto != precio_actual) or (ultimo.moneda != moneda):
                        ProveedorProductoPrecio.objects.create(
                            proveedor_producto_id=pp.proveedor_producto_id,
                            precio_neto=precio_actual,
                            moneda=moneda,
                        )

            # eliminar marcados para borrar
            for obj in formset.deleted_objects:
                obj.delete()

            # por consistencia (si algún día agregas m2m)
            formset.save_m2m()

            return redirect("compra_detail", pk=compra.pk)

        # Debug
        print("FORM errors:", form.errors)
        print("FORMSET errors:", formset.errors)
        print("FORMSET non form errors:", formset.non_form_errors())

        return render(request, "compras_app/compra_form.html", {
            "form": form,
            "formset": formset,
            "is_edit": False,
        })

    # GET
    form = CompraForm()
    formset = CompraItemFormSet(form_kwargs={"proveedor": None})

    return render(request, "compras_app/compra_form.html", {
        "form": form,
        "formset": formset,
        "is_edit": False,
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
        return ctx

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form = self.get_form()
        formset = self.get_context_data(form=form)["formset"]

        form_ok = form.is_valid()
        formset_ok = formset.is_valid()

        if form_ok and formset_ok:
            # detectar cambios ANTES de guardar
            header_changed = form.has_changed()
            items_changed = formset.has_changed()

            compra = form.save()

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

            # eliminar marcados
            for obj in formset.deleted_objects:
                obj.delete()

            # nro_linea para nuevos
            last = (CompraItem.objects.filter(compra=compra)
                    .aggregate(m=Max("nro_linea"))["m"] or 0)
            n = last + 1

            for it in items:
                if not it.pk:
                    it.nro_linea = n
                    n += 1

                it.compra = compra
                it.save()

                # Historial precio
                if it.producto_id:
                    pp, _ = ProveedorProducto.objects.get_or_create(
                        proveedor_id=compra.proveedor_id,
                        producto_id=it.producto_id,
                        defaults={"uom_compra": None},
                    )

                    precio_actual = it.precio_unitario or Decimal("0.00")
                    moneda = compra.moneda

                    ultimo = (ProveedorProductoPrecio.objects
                              .filter(proveedor_producto_id=pp.proveedor_producto_id)
                              .order_by("-proveedor_producto_precio_id")
                              .first())

                    if (not ultimo) or (ultimo.precio_neto != precio_actual) or (ultimo.moneda != moneda):
                        ProveedorProductoPrecio.objects.create(
                            proveedor_producto_id=pp.proveedor_producto_id,
                            precio_neto=precio_actual,
                            moneda=moneda,
                        )

            formset.save_m2m()

            return redirect("compra_detail", pk=compra.pk)

        # 👇 acá SIEMPRE verás errores cuando no guarda
        print("FORM errors:", form.errors)
        print("FORM changed_data:", form.changed_data)
        print("FORMSET errors:", formset.errors)
        print("FORMSET non_form_errors:", formset.non_form_errors())

        return self.render_to_response(self.get_context_data(form=form, formset=formset))

compra_update = CompraUpdateView.as_view()

#-------------- Proveeedor y producto -----------

def proveedor_productos(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)

    productos = ProveedorProducto.objects.select_related("producto").filter(
        proveedor=proveedor
    )

    return render(
        request,
        "compras_app/proveedor_productos.html",
        {
            "proveedor": proveedor,
            "productos": productos,
        },
    )

def productos_por_proveedor(request, proveedor_id):
    productos = Producto.objects.filter(
        proveedor_productos__proveedor_id=proveedor_id
    ).distinct().values("producto_id", "nombre")

    return JsonResponse(list(productos), safe=False)

# ----------- Distribución interna !!!!!!!!!!!!!!!!!!!! ------------
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
                it.save()  # en el model save() recalcula subtotales y recalcula totales del header

            for obj in formset.deleted_objects:
                obj.delete()

            formset.save_m2m()

            return redirect("factura_ic_detail", pk=factura.pk)

        return render(request, "compras_app/factura_ic_form.html", {
            "form": form,
            "formset": formset,
            "is_edit": False,
        })

    # GET
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
            # opcional: si quieres mostrar producto desde compra_item
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
                it.save()  # recalcula subtotales y header totales

            for obj in formset.deleted_objects:
                obj.delete()

            formset.save_m2m()

            # asegurar totales (por si borraron todo)
            factura.recalcular_totales(save=True)

            return redirect("factura_ic_detail", pk=factura.pk)

        return self.render_to_response(self.get_context_data(form=form, formset=formset))


factura_ic_update = FacturaICUpdateView.as_view()


def holding_por_codigo(request):
    codigo = request.GET.get("codigo")

    holding = Holding.objects.filter(codigo_empresa=codigo).first()
    if not holding:
        return JsonResponse({"ok": False})

    return JsonResponse({
        "ok": True,
        "id": holding.pk  # más seguro que holding_id
    })



def enviar_correo_oc(compra):
    subject = f"Solicitud autorización OC N° {compra.folio}"

    body = render_to_string("compras_app/oc_autorizacion.html", {"compra": compra})

    email = EmailMessage(
        subject=subject,
        body=body,
        to=["carolina.cheuquepil@dimarsa.cl"],
    )
    email.content_subtype = "html"

    # Adjuntar última cotización (COT) si existe
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

    # Registrar EMAIL en historial
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

    # Si Compra.estado es FK, debes asignar instancia (no string)
    estado_espera = EstadoDocumento.objects.get(nombre="En espera")
    compra.estado = estado_espera
    compra.save()

    enviar_correo_oc(compra)

    return redirect("compra_detail", pk=pk)



def cotizacion_upload(request, pk):
    compra = get_object_or_404(Compra, pk=pk)

    if request.method == "POST":
        form = CotizacionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            td_cot = TipoDocumento.objects.get(codigo="COT")
            estado_recibido = EstadoDocumento.objects.get(nombre="Recibido")

            h = form.save(commit=False)
            h.compra = compra
            h.tipo_documento = td_cot
            h.estado_documento = estado_recibido
            h.fecha_evento = timezone.now()
            h.save()

            return redirect("compra_detail", pk=compra.pk)
    else:
        form = CotizacionUploadForm()

    return render(request, "compras_app/cotizacion_upload.html", {
        "compra": compra,
        "form": form
    })
