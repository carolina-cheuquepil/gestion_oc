#PASO 3: CRUD completo 
#Para el Frontend

from django.shortcuts import render, redirect, get_object_or_404
from .models import Holding
from .serializers import HoldingSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import HoldingForm

class HoldingViewSet(ModelViewSet):
    queryset = Holding.objects.all()
    serializer_class = HoldingSerializer


def holding_frontend(request):
    holdings = Holding.objects.all()
    return render(request, "holding_app/holding_list.html", {"holdings": holdings})

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

