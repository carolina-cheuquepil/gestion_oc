from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.viewsets import ModelViewSet
from .models import Marca
from .serializers import MarcaSerializer
from .forms import MarcaForm


class MarcaViewSet(ModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer


def marcas_frontend(request):
    marcas = Marca.objects.all()
    return render(request, "producto_app/marca_list.html", {"marcas": marcas})


def marca_create(request):
    if request.method == "POST":
        form = MarcaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("marcas-lista")
    else:
        form = MarcaForm()
    return render(request, "producto_app/marca_form.html", {"form": form})


def marca_update(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    if request.method == "POST":
        form = MarcaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            return redirect("marcas-lista")
    else:
        form = MarcaForm(instance=marca)
    return render(request, "producto_app/marca_form.html", {"form": form, "marca": marca, "is_edit": True})
