#FrontEnd: Paso 1
from django import forms
from .models import Proveedor, Producto, Compra

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

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["producto_id", "nombre", "descripcion", "tipo_producto"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = [
            "tipo_documento",
            "estado_documento",
            "razon_social",
            "proveedor",
            "folio",
            "fecha_emision",
            "fecha_requerida",
            "moneda",
            "observacion",
            "total_neto",
            "total_iva",
            "total",
        ]

        widgets = {
            "fecha_emision": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "fecha_requerida": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "observacion": forms.Textarea(
                attrs={"rows": 3, "class": "form-control"}
            ),
            "folio": forms.TextInput(attrs={"class": "form-control"}),
            "total_neto": forms.NumberInput(attrs={"class": "form-control"}),
            "total_iva": forms.NumberInput(attrs={"class": "form-control"}),
            "total": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        total_neto = cleaned_data.get("total_neto") or 0
        total_iva = cleaned_data.get("total_iva") or 0
        total = cleaned_data.get("total") or 0

        if total != total_neto + total_iva:
            self.add_error(
                "total",
                "El total debe ser igual a la suma del neto más el IVA."
            )

        return cleaned_data
