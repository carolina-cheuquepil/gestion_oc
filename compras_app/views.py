#PASO 3: CRUD completo 
#FrontEnd: Paso 3

from django.shortcuts import render, redirect, get_object_or_404
from .models import Proveedor 
from .serializers import ProveedorSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import ProveedorForm

class ProveedorViewSet(ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer


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



