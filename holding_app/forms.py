#FrontEnd: Paso 1
from django import forms
from .models import Direccion, Holding, Sucursal
from django_select2.forms import ModelSelect2Widget

class HoldingForm(forms.ModelForm):
    empresa_estado = forms.TypedChoiceField(
        choices=[(True, "Activa"), (False, "No activa")],
        coerce=lambda value: value in (True, "True", "true", "1", 1),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Holding
        fields = ["codigo_empresa", "razon_social", "nombre", "rut_numero", "rut_dv", "empresa_estado"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class SucursalForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ["codigo_sucursal", "nombre", "activa"]
        widgets = {
            "codigo_sucursal": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ["calle", "numero", "ciudad", "comuna", "region"]
        widgets = {
            "calle": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "ciudad": forms.TextInput(attrs={"class": "form-control"}),
            "comuna": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        tiene_datos = any((cleaned.get(name) or "").strip() for name in self.fields)
        if tiene_datos and not (cleaned.get("calle") or "").strip():
            self.add_error("calle", "La calle es obligatoria si ingresas dirección.")
        if tiene_datos and not (cleaned.get("ciudad") or "").strip():
            self.add_error("ciudad", "La ciudad es obligatoria si ingresas dirección.")
        return cleaned

    def has_address_data(self):
        return any((self.cleaned_data.get(name) or "").strip() for name in self.fields)

class HoldingWidget(ModelSelect2Widget):
    model = Holding
    search_fields = [
        "razon_social__icontains",
        "nombre__icontains",
    ]

    def label_from_instance(self, obj):
        return obj.razon_social or obj.nombre

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        qs = super().filter_queryset(request, term, queryset, **dependent_fields)
        digits = "".join(c for c in (term or "") if c.isdigit())
        if digits:
            from django.db.models.functions import Cast
            from django.db.models import CharField
            pks = list(
                self.get_queryset()
                .annotate(codigo_str=Cast("codigo_empresa", output_field=CharField()))
                .filter(codigo_str__startswith=digits)
                .values_list("pk", flat=True)
            )
            if pks:
                qs = (qs | self.get_queryset().filter(pk__in=pks)).distinct()
        return qs

