#PASO 3: CRUD completo 
#PASO 2: Para el Frontend 

from django.shortcuts import render, redirect, get_object_or_404
from .models import Persona
from .serializers import PersonaSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import PersonaForm

class PersonaViewSet(ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer

#Paso 2
def persona_frontend(request):
    personas = Persona.objects.all()
    return render(request, "personas_app/personas_list.html", {"personas": personas})

def persona_create(request):
    if request.method == "POST":
        form = PersonaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("personas_ui")
    else:
        form = PersonaForm()

    return render(request, "personas_app/persona_form.html", {"form": form})

def persona_update(request, pk):
    persona = get_object_or_404(Persona, pk=pk)

    if request.method == "POST":
        form = PersonaForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            return redirect("personas_ui")
    else:
        form = PersonaForm(instance=persona)

    return render(
        request,
        "personas_app/persona_form.html",
        {"form": form, "persona": persona, "is_edit": True},
    )

