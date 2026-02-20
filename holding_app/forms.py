#FrontEnd: Paso 1
from django import forms
from .models import Holding
from django_select2.forms import ModelSelect2Widget

class HoldingForm(forms.ModelForm):
    empresa_estado = forms.ChoiceField(
        choices=[(True, "Activa"), (False, "No activa")],
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Holding
        fields = ["codigo_empresa", "razon_social", "nombre", "rut", "empresa_estado"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

class HoldingWidget(ModelSelect2Widget):
    model = Holding
    search_fields = [
        "razon_social__icontains",
        "codigo_empresa__icontains",
    ]

