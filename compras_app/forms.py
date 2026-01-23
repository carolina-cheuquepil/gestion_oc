#FrontEnd: Paso 1
from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    empresa_estado = forms.ChoiceField(
        choices=[(True, "Activa"), (False, "No activa")],
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Proveedor
        fields = ["proveedor_id", "razon_social", "nombre", "rut", "empresa_estado"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"