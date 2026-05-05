from datetime import date as date_cls
from decimal import Decimal
from functools import wraps
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from holding_app.access import (
    SESSION_TODAS_SUCURSALES,
    SESSION_USUARIO_ID,
    login_sucursal_required,
    sucursal_actual_id,
)
from holding_app.models import Sucursal
from .models import ActivoFijo, RecepcionCompraItem


SUCURSAL_CUSTODIA_INFORMATICA_ID = 22
CODIGO_INVENTARIO_PENDIENTE_PREFIX = "PEND-AF-"
ESTADOS_ACTIVO = ["En bodega", "En uso", "En reparacion", "Dado de baja"]


def login_usuario_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get(SESSION_USUARIO_ID):
            return redirect(f"{reverse('login')}?next={request.get_full_path()}")
        return view_func(request, *args, **kwargs)

    return wrapper


def _activos_queryset():
    return ActivoFijo.objects.select_related(
        "producto",
        "proyecto_informatica",
        "sucursal__empresa",
        "recepcion_compra_item__compra_item__compra",
    )


def _sucursal_custodia_informatica():
    return get_object_or_404(
        Sucursal.objects.select_related("empresa"),
        pk=SUCURSAL_CUSTODIA_INFORMATICA_ID,
        activa=True,
    )


def _folio_factura_ic_activo(activo):
    return f"IC-AF-{activo.activo_fijo_id}-{date_cls.today().strftime('%Y%m%d')}"


def _codigo_inventario_pendiente(recepcion_id, unit_num):
    return f"{CODIGO_INVENTARIO_PENDIENTE_PREFIX}{recepcion_id}-{unit_num}-{uuid4().hex[:8]}"


def _codigo_inventario_pendiente_activo(activo):
    return (activo.codigo_inventario or "").startswith(CODIGO_INVENTARIO_PENDIENTE_PREFIX)


@login_sucursal_required
def activos_fijos_list(request):
    activos = _activos_queryset().filter(
        sucursal_id=sucursal_actual_id(request),
    ).order_by("sucursal__nombre", "nombre_activo")
    return render(request, "activos_app/activos_list.html", {
        "activos": activos,
        "codigo_pendiente_prefix": CODIGO_INVENTARIO_PENDIENTE_PREFIX,
    })


@login_usuario_required
def activos_informatica_list(request):
    activos = _activos_queryset().filter(
        sucursal_id=SUCURSAL_CUSTODIA_INFORMATICA_ID,
    ).order_by("nombre_activo")
    return render(request, "activos_app/activos_list.html", {
        "activos": activos,
        "titulo": "Activos en Informatica",
        "subtitulo": "Custodia Informatica 6 piso",
        "empty_message": "No hay activos fijos en custodia de Informatica.",
        "codigo_pendiente_prefix": CODIGO_INVENTARIO_PENDIENTE_PREFIX,
    })


@transaction.atomic
@login_usuario_required
def traspasar_activo_fijo(request, activo_pk):
    from compras_app.models import FacturaIntercompany, FacturaIntercompanyItem, ProyectoInformatica

    activos_disponibles = ActivoFijo.objects.select_related(
        "producto",
        "proyecto_informatica",
        "sucursal__empresa",
        "recepcion_compra_item__compra_item__compra__moneda",
    )
    if not request.session.get(SESSION_TODAS_SUCURSALES):
        activos_disponibles = activos_disponibles.filter(sucursal_id=sucursal_actual_id(request))
    activos_disponibles = activos_disponibles | ActivoFijo.objects.select_related(
        "producto",
        "proyecto_informatica",
        "sucursal__empresa",
        "recepcion_compra_item__compra_item__compra__moneda",
    ).filter(sucursal_id=SUCURSAL_CUSTODIA_INFORMATICA_ID)

    activo = get_object_or_404(activos_disponibles.distinct(), pk=activo_pk)

    compra_item = None
    compra = None
    if activo.recepcion_compra_item_id:
        compra_item = activo.recepcion_compra_item.compra_item
        compra = compra_item.compra

    sucursales = Sucursal.objects.select_related("empresa").filter(activa=True)
    if not request.session.get(SESSION_TODAS_SUCURSALES):
        sucursales = sucursales.filter(
            usuario_sucursales__usuario_id=request.session.get(SESSION_USUARIO_ID),
        )
    sucursales = sucursales.exclude(pk=activo.sucursal_id).order_by("nombre").distinct()
    proyectos = ProyectoInformatica.objects.filter(activo=True).order_by("proyecto_nombre")
    errores = []

    codigo_pendiente = _codigo_inventario_pendiente_activo(activo)
    val_codigo_inventario = "" if codigo_pendiente else activo.codigo_inventario
    val_numero_serie = activo.numero_serie or ""
    val_folio_factura_ic = ""
    val_proyecto_informatica_id = str(activo.proyecto_informatica_id or "")

    if request.method == "POST":
        val_codigo_inventario = (request.POST.get("codigo_inventario") or "").strip()
        val_numero_serie = (request.POST.get("numero_serie") or "").strip()
        val_folio_factura_ic = (request.POST.get("folio_factura_ic") or "").strip()
        val_proyecto_informatica_id = (request.POST.get("proyecto_informatica") or "").strip()
        sucursal_destino_id = request.POST.get("sucursal_destino")
        sucursal_destino = Sucursal.objects.select_related("empresa").filter(
            pk=sucursal_destino_id,
            activa=True,
        ).first()
        proyecto_informatica = None
        if val_proyecto_informatica_id:
            try:
                proyecto_informatica = ProyectoInformatica.objects.filter(
                    pk=int(val_proyecto_informatica_id),
                    activo=True,
                ).first()
            except ValueError:
                proyecto_informatica = None

            if proyecto_informatica is None:
                errores.append("Selecciona un proyecto de Informatica activo.")

        if not val_codigo_inventario:
            errores.append("Ingresa el codigo de inventario antes de entregar el activo.")
        elif val_codigo_inventario.startswith(CODIGO_INVENTARIO_PENDIENTE_PREFIX):
            errores.append("Ingresa un codigo de inventario definitivo.")
        elif ActivoFijo.objects.filter(codigo_inventario=val_codigo_inventario).exclude(pk=activo.pk).exists():
            errores.append(f"El codigo de inventario '{val_codigo_inventario}' ya existe.")

        if not val_numero_serie:
            errores.append("Ingresa el numero de serie antes de entregar el activo.")

        if not val_folio_factura_ic:
            errores.append("Ingresa el folio de la Factura Intercompany.")
        elif len(val_folio_factura_ic) > 30:
            errores.append("El folio de la Factura Intercompany no puede superar 30 caracteres.")

        if not sucursal_destino:
            errores.append("Selecciona una sucursal destino activa.")
        elif sucursal_destino.pk == activo.sucursal_id:
            errores.append("La sucursal destino debe ser distinta a la sucursal actual.")
        elif sucursal_destino.empresa_id == activo.sucursal.empresa_id:
            errores.append(
                "Para facturacion intercompany, la sucursal destino debe pertenecer a otra empresa."
            )

        if not compra_item or not compra:
            errores.append(
                "Este activo no tiene una recepcion de compra asociada para generar factura intercompany."
            )

        if not errores:
            factura = FacturaIntercompany.objects.create(
                empresa_emisora=activo.sucursal.empresa,
                empresa_receptora=sucursal_destino.empresa,
                compra_origen=compra,
                folio=val_folio_factura_ic,
                fecha_emision=date_cls.today(),
                moneda=compra.moneda,
                recargo_porcentaje=Decimal("5.00"),
            )

            try:
                FacturaIntercompanyItem.objects.create(
                    factura_ic=factura,
                    compra_item=compra_item,
                    cantidad=Decimal("1.000"),
                    precio_base=activo.valor or compra_item.precio_unitario or Decimal("0.00"),
                    afecta_iva=compra_item.afecta_iva,
                    iva_porcentaje=compra_item.iva_porcentaje,
                )
            except ValidationError as exc:
                factura.delete()
                if hasattr(exc, "message_dict"):
                    for msgs in exc.message_dict.values():
                        errores.extend(msgs)
                else:
                    errores.extend(exc.messages)

            if not errores:
                activo.sucursal = sucursal_destino
                activo.codigo_inventario = val_codigo_inventario
                activo.numero_serie = val_numero_serie
                activo.proyecto_informatica = proyecto_informatica
                activo.estado = "En uso" if activo.estado == "En bodega" else activo.estado
                activo.observacion = (
                    f"{activo.observacion or ''}\n"
                    f"Traspaso a {sucursal_destino.nombre}; Factura IC {factura.folio}."
                ).strip()
                activo.save(update_fields=[
                    "sucursal",
                    "codigo_inventario",
                    "numero_serie",
                    "proyecto_informatica",
                    "estado",
                    "observacion",
                ])
                return redirect("factura_ic_detail", pk=factura.pk)

    return render(request, "activos_app/activo_traspaso_form.html", {
        "activo": activo,
        "codigo_pendiente": codigo_pendiente,
        "val_codigo_inventario": val_codigo_inventario,
        "val_numero_serie": val_numero_serie,
        "val_folio_factura_ic": val_folio_factura_ic,
        "val_proyecto_informatica_id": val_proyecto_informatica_id,
        "compra_item": compra_item,
        "compra": compra,
        "proyectos": proyectos,
        "sucursales": sucursales,
        "errores": errores,
    })


@transaction.atomic
@login_usuario_required
def registrar_activos_fijos(request, compra_pk):
    from compras_app.models import Compra

    sucursal_custodia = _sucursal_custodia_informatica()

    compra = get_object_or_404(
        Compra.objects.select_related("razon_social", "proveedor"),
        pk=compra_pk,
    )

    recp_param = request.GET.get("recp", "") or request.POST.get("recp", "")
    try:
        recp_ids = [int(x) for x in recp_param.split(",") if x.strip()]
    except ValueError:
        recp_ids = []

    recepciones = RecepcionCompraItem.objects.filter(
        recepcion_compra_item_id__in=recp_ids,
        compra_item__compra_id=compra.pk,
    ).select_related(
        "compra_item__producto__tipo_producto",
    )

    af_recepciones = [
        r for r in recepciones
        if r.compra_item.producto_id
        and "activo" in r.compra_item.producto.tipo_producto.nombre.lower()
    ]

    units = []
    for recepcion in af_recepciones:
        item = recepcion.compra_item
        producto = item.producto
        cantidad = max(1, int(recepcion.cantidad_recibida))
        for i in range(cantidad):
            units.append({
                "recepcion": recepcion,
                "item": item,
                "producto": producto,
                "sucursal": sucursal_custodia,
                "prefix": f"af_{recepcion.recepcion_compra_item_id}_{i}",
                "valor_default": item.precio_unitario,
                "nombre_default": producto.producto_nombre,
                "fecha_default": date_cls.today().isoformat(),
                "unit_num": i + 1,
                "total_unidades": cantidad,
            })

    errores = []

    if request.method == "POST":
        activos_a_crear = []

        for unit in units:
            prefix = unit["prefix"]
            unit["val_nombre"] = request.POST.get(f"{prefix}_nombre", unit["nombre_default"])
            unit["val_fecha"] = request.POST.get(f"{prefix}_fecha", unit["fecha_default"])
            unit["val_valor"] = request.POST.get(f"{prefix}_valor", str(unit["valor_default"]))
            unit["val_estado"] = request.POST.get(f"{prefix}_estado", "En bodega")

            nombre = unit["val_nombre"].strip()
            fecha_str = unit["val_fecha"].strip()
            valor_str = unit["val_valor"].strip() or "0"
            estado = unit["val_estado"].strip()

            if not nombre or not fecha_str:
                errores.append(
                    f"Completa nombre y fecha para '{unit['nombre_default']}' unidad {unit['unit_num']}."
                )
                continue

            try:
                fecha_adq = date_cls.fromisoformat(fecha_str)
                valor = Decimal(valor_str) if valor_str else Decimal("0")
            except Exception:
                errores.append(f"Fecha o valor invalido para '{nombre}'.")
                continue

            activos_a_crear.append(ActivoFijo(
                producto=unit["producto"],
                sucursal=unit["sucursal"],
                nombre_activo=nombre,
                codigo_inventario=_codigo_inventario_pendiente(
                    unit["recepcion"].recepcion_compra_item_id,
                    unit["unit_num"],
                ),
                numero_serie=None,
                fecha_adquisicion=fecha_adq,
                valor=valor,
                estado=estado,
                recepcion_compra_item=unit["recepcion"],
            ))

        if not errores and len(activos_a_crear) == len(units):
            for activo in activos_a_crear:
                activo.save()
            return redirect("compra_detail", pk=compra.pk)
    else:
        for unit in units:
            unit["val_nombre"] = unit["nombre_default"]
            unit["val_fecha"] = unit["fecha_default"]
            unit["val_valor"] = str(unit["valor_default"])
            unit["val_estado"] = "En bodega"

    return render(request, "activos_app/activos_fijos_form.html", {
        "compra": compra,
        "units": units,
        "recp_param": recp_param,
        "errores": errores,
        "estados": ESTADOS_ACTIVO,
    })
