from django.shortcuts import render, redirect, get_object_or_404
from .models import Proveedor, Producto, ProveedorProducto
from .serializers import ProveedorSerializer, ProductoSerializer
from .forms import ProveedorForm, ProductoForm, ProveedorProductoForm
from rest_framework.viewsets import ModelViewSet
from django.db import transaction
from django.http import JsonResponse


class ProveedorViewSet(ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer


class ProductoViewSet(ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer


# ----------- Proveedores ------------
def proveedores_frontend(request):
    q = request.GET.get("q", "").strip()
    proveedores = Proveedor.objects.all()
    if q:
        from django.db.models import Q
        proveedores = proveedores.filter(
            Q(nombre__icontains=q) |
            Q(razon_social__icontains=q) |
            Q(rut_numero__icontains=q)
        )
    return render(request, "proveedores_app/proveedores_list.html", {"proveedores": proveedores, "q": q})


def proveedor_create(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("proveedores-lista")
    else:
        form = ProveedorForm()
    return render(request, "proveedores_app/proveedor_form.html", {"form": form})


def proveedor_update(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            return redirect("proveedores-lista")
    else:
        form = ProveedorForm(instance=proveedor)
    return render(
        request,
        "proveedores_app/proveedor_form.html",
        {"form": form, "proveedor": proveedor, "is_edit": True},
    )


# ----------- Productos ------------
def productos_frontend(request):
    from django.db.models import Q
    q = request.GET.get("q", "").strip()
    productos = ProveedorProducto.objects.select_related(
        "producto", "producto__tipo_producto", "producto__marca", "proveedor"
    )
    if q:
        productos = productos.filter(
            Q(producto__sku__icontains=q) |
            Q(producto__producto_nombre__icontains=q) |
            Q(producto__tipo_producto__nombre__icontains=q) |
            Q(producto__marca__marca_nombre__icontains=q) |
            Q(producto__descripcion__icontains=q) |
            Q(proveedor__nombre__icontains=q) |
            Q(proveedor__razon_social__icontains=q)
        )
    return render(request, "proveedores_app/productos_list.html", {"productos": productos, "q": q})


def producto_create(request):
    proveedor_id = request.GET.get("proveedor_id")
    proveedor = None
    if proveedor_id:
        proveedor = get_object_or_404(Proveedor, pk=proveedor_id)

    if request.method == "POST":
        form = ProductoForm(request.POST)
        if proveedor:
            rel_form = ProveedorProductoForm(request.POST, initial={"proveedor": proveedor})
        else:
            rel_form = ProveedorProductoForm(request.POST)

        if form.is_valid() and rel_form.is_valid():
            with transaction.atomic():
                producto = form.save()
                rel = rel_form.save(commit=False)
                rel.producto = producto
                if proveedor:
                    rel.proveedor = proveedor
                rel.save()
            return redirect("productos-lista")
    else:
        form = ProductoForm()
        rel_form = ProveedorProductoForm(initial={"proveedor": proveedor} if proveedor else None)

    return render(request, "proveedores_app/producto_form.html", {
        "form": form,
        "rel_form": rel_form,
        "is_edit": False,
        "proveedor_fijado": bool(proveedor),
        "proveedor": proveedor,
    })


def producto_update(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    relacion, _ = ProveedorProducto.objects.get_or_create(
        producto=producto,
    )

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        rel_form = ProveedorProductoForm(request.POST, instance=relacion)
        if form.is_valid() and rel_form.is_valid():
            with transaction.atomic():
                form.save()
                rel_form.save()
            return redirect("productos-lista")
    else:
        form = ProductoForm(instance=producto)
        rel_form = ProveedorProductoForm(instance=relacion)

    return render(request, "proveedores_app/producto_form.html", {
        "form": form,
        "rel_form": rel_form,
        "producto": producto,
        "is_edit": True,
    })


def proveedor_productos(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    productos = ProveedorProducto.objects.select_related("producto").filter(proveedor=proveedor)
    return render(
        request,
        "proveedores_app/proveedor_productos.html",
        {"proveedor": proveedor, "productos": productos},
    )


def proveedor_buscar(request):
    rut = request.GET.get("rut", "").strip()
    razon = request.GET.get("razon", "").strip()
    proveedor_id = request.GET.get("id", "").strip()
    try:
        if proveedor_id and proveedor_id.isdigit():
            p = Proveedor.objects.get(pk=int(proveedor_id))
        elif rut and rut.isdigit():
            p = Proveedor.objects.get(rut_numero=int(rut))
        elif razon:
            p = Proveedor.objects.filter(razon_social__icontains=razon).first()
            if not p:
                return JsonResponse({"error": "No encontrado"}, status=404)
        else:
            return JsonResponse({"error": "Parámetro inválido"}, status=400)
        return JsonResponse({
            "id": p.pk,
            "rut_numero": p.rut_numero,
            "rut_dv": p.rut_dv,
            "razon_social": p.razon_social,
        })
    except Proveedor.DoesNotExist:
        return JsonResponse({"error": "No encontrado"}, status=404)


def producto_create_ajax(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "errors": "Método no permitido"}, status=405)
    form = ProductoForm(request.POST)
    proveedor_id = request.POST.get("proveedor_id")
    proveedor = None
    if proveedor_id:
        try:
            proveedor = Proveedor.objects.get(pk=int(proveedor_id))
        except (Proveedor.DoesNotExist, ValueError):
            pass
    if form.is_valid():
        with transaction.atomic():
            producto = form.save()
            if proveedor:
                ProveedorProducto.objects.get_or_create(proveedor=proveedor, producto=producto)
        return JsonResponse({
            "ok": True,
            "producto_id": producto.producto_id,
            "producto_nombre": producto.producto_nombre,
            "sku": producto.sku or "",
            "descripcion": producto.descripcion or "",
        })
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


def productos_por_proveedor(request, proveedor_id):
    productos = Producto.objects.filter(
        proveedor_productos__proveedor_id=proveedor_id
    ).distinct().values("producto_id", "producto_nombre", "sku", "descripcion", "uom", "tipo_producto_id", "tipo_producto__nombre")
    return JsonResponse(list(productos), safe=False)


