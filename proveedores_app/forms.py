from django import forms
from django.forms import BaseFormSet, formset_factory
from django.db.models import Max
from django.db.models import Q, CharField
from django.db.models.functions import Cast
from django_select2.forms import ModelSelect2Widget
from .models import Contacto, Proveedor, Producto, ProveedorContacto, ProveedorProducto


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


class ContactoProveedorForm(forms.Form):
    proveedor_contacto_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    contacto_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    nombres = forms.CharField(max_length=80, required=False)
    apellidos = forms.CharField(max_length=100, required=False)
    email = forms.EmailField(max_length=120, required=False)
    celular = forms.CharField(max_length=20, required=False)
    es_principal = forms.BooleanField(required=False)
    activo = forms.BooleanField(required=False, initial=True)
    DELETE = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned

        has_contact_data = any(
            cleaned.get(field)
            for field in ("nombres", "apellidos", "email", "celular")
        )
        has_existing_id = cleaned.get("proveedor_contacto_id") or cleaned.get("contacto_id")
        if has_contact_data or has_existing_id:
            if not cleaned.get("nombres"):
                self.add_error("nombres", "Ingresa los nombres del contacto.")
            if not cleaned.get("apellidos"):
                self.add_error("apellidos", "Ingresa los apellidos del contacto.")
        return cleaned

    @property
    def is_blank(self):
        if not hasattr(self, "cleaned_data"):
            return False
        return not any(
            self.cleaned_data.get(field)
            for field in ("proveedor_contacto_id", "contacto_id", "nombres", "apellidos", "email", "celular")
        )


class BaseContactoProveedorFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        principal_count = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE") or form.is_blank:
                continue
            if form.cleaned_data.get("es_principal"):
                principal_count += 1
        if principal_count > 1:
            raise forms.ValidationError("Solo un contacto puede quedar marcado como principal.")


ContactoProveedorFormSet = formset_factory(
    ContactoProveedorForm,
    formset=BaseContactoProveedorFormSet,
    extra=1,
    can_delete=False,
)


def contactos_initial_for_proveedor(proveedor):
    if not proveedor:
        return []
    relaciones = proveedor.contactos_relacion.select_related("contacto").order_by(
        "-es_principal",
        "contacto__apellidos",
        "contacto__nombres",
    )
    return [
        {
            "proveedor_contacto_id": relacion.proveedor_contacto_id,
            "contacto_id": relacion.contacto_id,
            "nombres": relacion.contacto.nombres,
            "apellidos": relacion.contacto.apellidos,
            "email": relacion.contacto.email,
            "celular": relacion.contacto.celular,
            "es_principal": relacion.es_principal,
            "activo": relacion.activo,
        }
        for relacion in relaciones
    ]


def _next_contacto_id():
    return (Contacto.objects.aggregate(max_id=Max("contacto_id"))["max_id"] or 0) + 1


def save_contactos_proveedor(proveedor, formset):
    for form in formset:
        if not hasattr(form, "cleaned_data"):
            continue
        data = form.cleaned_data
        relacion_id = data.get("proveedor_contacto_id")
        contacto_id = data.get("contacto_id")

        if data.get("DELETE"):
            if relacion_id:
                ProveedorContacto.objects.filter(
                    proveedor=proveedor,
                    proveedor_contacto_id=relacion_id,
                ).delete()
            continue

        if form.is_blank:
            continue

        if contacto_id:
            contacto = Contacto.objects.get(pk=contacto_id)
        else:
            contacto = Contacto(contacto_id=_next_contacto_id())

        contacto.nombres = data["nombres"]
        contacto.apellidos = data["apellidos"]
        contacto.email = data.get("email") or None
        contacto.celular = data.get("celular") or None
        contacto.save()

        if relacion_id:
            relacion = ProveedorContacto.objects.get(
                proveedor=proveedor,
                proveedor_contacto_id=relacion_id,
            )
            relacion.contacto = contacto
        else:
            relacion, _ = ProveedorContacto.objects.get_or_create(
                proveedor=proveedor,
                contacto=contacto,
            )
        relacion.es_principal = bool(data.get("es_principal"))
        relacion.activo = bool(data.get("activo"))
        relacion.save()


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["producto_nombre", "descripcion", "marca", "sku", "uom", "tipo_producto"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marca"].queryset = self.fields["marca"].queryset.order_by("marca_nombre")
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
