#PASO 3: CRUD completo 
#Para el Frontend

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Holding
from .serializers import HoldingSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import HoldingForm

class HoldingViewSet(ModelViewSet):
    queryset = Holding.objects.all()
    serializer_class = HoldingSerializer


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


def holding_frontend(request):
    holdings = Holding.objects.all()
    codigo = request.GET.get("codigo", "").strip()
    if codigo:
        holdings = holdings.filter(codigo_empresa=codigo) if codigo.isdigit() else holdings.none()
    return render(request, "holding_app/holding_list.html", {"holdings": holdings, "codigo": codigo})

def holding_create(request):
    if request.method == "POST":
        form = HoldingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("holdings_ui")
    else:
        form = HoldingForm()

    return render(request, "holding_app/holding_form.html", {"form": form})

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

