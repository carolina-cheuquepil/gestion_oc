from django import forms
from django.db.models import Q, CharField
from django.db.models.functions import Cast
from django_select2.forms import ModelSelect2Widget
from .models import Proveedor, Producto, ProveedorProducto


class ProveedorWidget(ModelSelect2Widget):
    model = Proveedor
    search_fields = ["rut_numero__icontains", "razon_social__icontains"]  # requerido por django-select2; la búsqueda real se hace en filter_queryset

    def label_from_instance(self, obj):
        return obj.razon_social

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        if queryset is None:
            queryset = self.get_queryset()
        term = (term or "").strip()
        if not term:
            return queryset.none()

        queryset = queryset.annotate(rut_str=Cast("rut_numero", output_field=CharField()))
        filtros = Q(razon_social__icontains=term)

        digits = "".join(c for c in term if c.isdigit())
        if digits:
            filtros |= Q(rut_str__startswith=digits)

        return queryset.filter(filtros).distinct()


class ProveedorForm(forms.ModelForm):
    empresa_estado = forms.ChoiceField(
        choices=[(True, "Activa"), (False, "No activa")],
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Proveedor
        fields = ["proveedor_id", "razon_social", "nombre", "rut_numero", "rut_dv", "empresa_estado"]

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
        fields = ["producto_nombre", "descripcion", "marca", "sku", "uom", "tipo_producto"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class ProveedorProductoForm(forms.ModelForm):
    class Meta:
        model = ProveedorProducto
        fields = ["proveedor"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get("proveedor"):
            self.fields["proveedor"].disabled = True

