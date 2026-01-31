#PASO 3° BD: CRUD completo 
#FrontEnd: Paso 3


from django.shortcuts import render, redirect, get_object_or_404
from .models import Proveedor, Producto, Compra, HistorialCompra
from .serializers import ProveedorSerializer, ProductoSerializer, CompraSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import ProveedorForm, ProductoForm, CompraForm
from django.views.generic import UpdateView
from django.urls import reverse_lazy

class ProveedorViewSet(ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer

class ProductoViewSet(ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CompraViewSet(ModelViewSet):
    queryset =  Compra.objects.all()
    serializer_class = CompraSerializer


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

def productos_frontend(request):
    productos = Producto.objects.all()
    return render(request, "compras_app/productos_list.html", {"productos": productos})

#FrontEnd: Paso 3
def producto_create(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("productos_ui")
    else:
        form = ProductoForm()

    return render(request, "compras_app/producto_form.html", {"form": form})

def producto_update(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect("productos_ui")
    else:
        form = ProductoForm(instance=producto)

    return render(
        request,
        "compras_app/producto_form.html",
        {"form": form, "producto": producto, "is_edit": True},
    )

def compras_frontend(request):
    compras = Compra.objects.all()
    return render(request, "compras_app/compras_list.html", {"compras": compras})

def compra_detail(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    return render(request, "compras_app/compra_detail.html", {"compra": compra})

class CompraUpdateView(UpdateView):
    model = Compra
    form_class = CompraForm
    template_name = "compras_app/compra_form.html"

    def get_success_url(self):
        return reverse_lazy("compra_detail", kwargs={"pk": self.object.pk})

compra_update = CompraUpdateView.as_view()

class CompraUpdateView(UpdateView):
    model = Compra
    form_class = CompraForm
    template_name = "compras_app/compra_form.html"

    def form_valid(self, form):
        compra = form.save()  # guarda cambios en compra

        # crea snapshot en historial
        HistorialCompra.objects.create(
            compra=compra,
            tipo_documento=compra.tipo_documento,
            estado_documento=compra.estado_documento,
            folio=compra.folio,
            usuario=self.request.user if self.request.user.is_authenticated else None,
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("compra_detail", kwargs={"pk": self.object.pk})





