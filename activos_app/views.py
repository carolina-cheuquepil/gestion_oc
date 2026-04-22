from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from decimal import Decimal
from datetime import date as date_cls
from .models import RecepcionCompraItem, ActivoFijo, Sucursal


def activos_fijos_list(request):
    activos = ActivoFijo.objects.select_related(
        "producto", "sucursal", "recepcion_compra_item__compra_item__compra"
    ).order_by("sucursal__nombre", "nombre_activo")
    return render(request, "activos_app/activos_list.html", {"activos": activos})

ESTADOS_ACTIVO = ["En bodega", "En uso", "En reparación", "Dado de baja"]


@transaction.atomic
def registrar_activos_fijos(request, compra_pk):
    from compras_app.models import Compra

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
    ).select_related(
        "compra_item__producto__tipo_producto",
        "compra_item__sucursal",
    )

    # Solo ítems cuyo tipo_producto contiene "activo" en el nombre
    af_recepciones = [
        r for r in recepciones
        if r.compra_item.producto_id
        and "activo" in r.compra_item.producto.tipo_producto.nombre.lower()
    ]

    # Una fila por unidad recibida (cantidad entera)
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
                "sucursal": item.sucursal,
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
        codigos_nuevos = set()

        # Recuperar valores ingresados para repoblar el form en caso de error
        for unit in units:
            prefix = unit["prefix"]
            unit["val_nombre"] = request.POST.get(f"{prefix}_nombre", unit["nombre_default"])
            unit["val_codigo"] = request.POST.get(f"{prefix}_codigo", "")
            unit["val_serie"] = request.POST.get(f"{prefix}_serie", "")
            unit["val_fecha"] = request.POST.get(f"{prefix}_fecha", unit["fecha_default"])
            unit["val_valor"] = request.POST.get(f"{prefix}_valor", str(unit["valor_default"]))
            unit["val_estado"] = request.POST.get(f"{prefix}_estado", "En bodega")

            nombre = unit["val_nombre"].strip()
            codigo = unit["val_codigo"].strip()
            serie = unit["val_serie"].strip()
            fecha_str = unit["val_fecha"].strip()
            valor_str = unit["val_valor"].strip() or "0"
            estado = unit["val_estado"].strip()

            if not nombre or not codigo or not fecha_str:
                errores.append(
                    f"Completa nombre, código inventario y fecha para "
                    f"'{unit['nombre_default']}' unidad {unit['unit_num']}."
                )
                continue

            if ActivoFijo.objects.filter(codigo_inventario=codigo).exists():
                errores.append(f"El código de inventario '{codigo}' ya existe.")
                continue

            if codigo in codigos_nuevos:
                errores.append(f"El código '{codigo}' está duplicado en este formulario.")
                continue

            try:
                fecha_adq = date_cls.fromisoformat(fecha_str)
                valor = Decimal(valor_str) if valor_str else Decimal("0")
            except Exception:
                errores.append(f"Fecha o valor inválido para '{nombre}'.")
                continue

            codigos_nuevos.add(codigo)
            activos_a_crear.append(ActivoFijo(
                producto=unit["producto"],
                sucursal=unit["sucursal"],
                nombre_activo=nombre,
                codigo_inventario=codigo,
                numero_serie=serie or None,
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
        # Valores iniciales para GET
        for unit in units:
            unit["val_nombre"] = unit["nombre_default"]
            unit["val_codigo"] = ""
            unit["val_serie"] = ""
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
