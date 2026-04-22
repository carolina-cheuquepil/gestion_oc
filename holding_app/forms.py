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
        fields = ["codigo_empresa", "razon_social", "nombre", "rut_numero", "rut_dv", "empresa_estado"]
    
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

