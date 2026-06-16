import json

#FrontEnd: Paso 1
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory, modelformset_factory
from .models import (
    Direccion,
    Holding,
    SegmentoRed,
    Sucursal,
    SucursalArea,
    SucursalPiso,
    SucursalTelefono,
)
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
        fields = ["calle", "numero", "complemento", "ciudad", "comuna", "region"]
        widgets = {
            "calle": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "complemento": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Depto., oficina, local, piso...",
                }
            ),
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


class SucursalTelefonoForm(forms.ModelForm):
    class Meta:
        model = SucursalTelefono
        fields = ["sucursal_area", "tipo_telefono", "numero", "principal"]
        labels = {
            "sucursal_area": "Area",
            "tipo_telefono": "Tipo de telefono",
            "numero": "Numero",
            "principal": "Principal",
        }
        widgets = {
            "sucursal_area": forms.Select(attrs={"class": "form-select"}),
            "tipo_telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Fijo, WhatsApp, central..."}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "principal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SucursalTelefonoFormSetBase(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        area_qs = SucursalArea.objects.none()
        if self.instance and self.instance.pk:
            area_qs = SucursalArea.objects.filter(
                sucursal_piso__sucursal=self.instance
            ).order_by("sucursal_piso__piso", "tipo", "area")
        for form in self.forms:
            if "sucursal_area" in form.fields:
                form.fields["sucursal_area"].queryset = area_qs

    def clean(self):
        super().clean()
        if not self.instance or not self.instance.pk:
            return
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            sucursal_area = form.cleaned_data.get("sucursal_area")
            if (
                sucursal_area
                and sucursal_area.sucursal_piso.sucursal_id != self.instance.pk
            ):
                form.add_error("sucursal_area", "El area debe pertenecer a esta sucursal.")


SucursalTelefonoFormSet = inlineformset_factory(
    Sucursal,
    SucursalTelefono,
    form=SucursalTelefonoForm,
    formset=SucursalTelefonoFormSetBase,
    extra=1,
    can_delete=True,
)


class SucursalAreaForm(forms.ModelForm):
    class Meta:
        model = SucursalArea
        fields = ["sucursal_piso", "area", "tipo", "activa"]
        labels = {
            "sucursal_piso": "Piso",
            "area": "Area",
            "tipo": "Tipo",
            "activa": "Activa",
        }
        widgets = {
            "sucursal_piso": forms.Select(attrs={"class": "form-select"}),
            "area": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Ventas, Piso 2, Bodega central"}),
            "tipo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Piso, Area, Bodega, Departamento"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        pisos_queryset = kwargs.pop("pisos_queryset", SucursalPiso.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["sucursal_piso"].required = True
        self.fields["sucursal_piso"].queryset = pisos_queryset


SucursalAreaFormSet = modelformset_factory(
    SucursalArea,
    form=SucursalAreaForm,
    extra=1,
    can_delete=True,
)


class SucursalPisoForm(forms.ModelForm):
    class Meta:
        model = SucursalPiso
        fields = ["piso", "activo"]
        labels = {
            "piso": "Piso",
            "activo": "Activo",
        }
        widgets = {
            "piso": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Piso 1, Subterraneo"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


SucursalPisoFormSet = inlineformset_factory(
    Sucursal,
    SucursalPiso,
    form=SucursalPisoForm,
    extra=1,
    can_delete=True,
)


class SegmentoRedForm(forms.ModelForm):
    red_guardada = forms.ChoiceField(
        required=False,
        label="Red guardada",
        choices=(),
        widget=forms.Select(attrs={"class": "form-select red-guardada-select"}),
    )

    class Meta:
        model = SegmentoRed
        fields = ["sucursal_area", "segmento", "segmento_nombre", "activa"]
        labels = {
            "sucursal_area": "Area",
            "segmento": "Segmento",
            "segmento_nombre": "Nombre segmento",
            "activa": "Activa",
        }
        widgets = {
            "sucursal_area": forms.Select(attrs={"class": "form-select"}),
            "segmento": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: VLAN 10"}),
            "segmento_nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Administracion"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        redes_guardadas = kwargs.pop("redes_guardadas", None)
        super().__init__(*args, **kwargs)
        self.fields["segmento"].required = False
        self.fields["segmento_nombre"].required = False
        if redes_guardadas is None:
            redes_guardadas = list(
                SegmentoRed.objects.filter(activa=True)
                .exclude(segmento="")
                .exclude(segmento_nombre="")
                .values_list("segmento", "segmento_nombre")
                .distinct()
                .order_by("segmento", "segmento_nombre")
            )
        self.fields["red_guardada"].choices = [
            ("", "Seleccionar una red guardada...")
        ] + [
            (json.dumps([segmento, nombre]), f"{segmento} - {nombre}")
            for segmento, nombre in redes_guardadas
        ]

    def clean(self):
        cleaned = super().clean()
        red_guardada = cleaned.get("red_guardada")
        if red_guardada:
            segmento, segmento_nombre = json.loads(red_guardada)
            cleaned["segmento"] = segmento
            cleaned["segmento_nombre"] = segmento_nombre
            self.instance.segmento = segmento
            self.instance.segmento_nombre = segmento_nombre
        else:
            if not cleaned.get("segmento"):
                self.add_error("segmento", "Ingresa un segmento o selecciona una red guardada.")
            if not cleaned.get("segmento_nombre"):
                self.add_error("segmento_nombre", "Ingresa un nombre o selecciona una red guardada.")
        return cleaned


class SegmentoRedFormSetBase(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.redes_guardadas = list(
            SegmentoRed.objects.filter(activa=True)
            .exclude(segmento="")
            .exclude(segmento_nombre="")
            .values_list("segmento", "segmento_nombre")
            .distinct()
            .order_by("segmento", "segmento_nombre")
        )
        super().__init__(*args, **kwargs)
        area_qs = SucursalArea.objects.none()
        if self.instance and self.instance.pk:
            area_qs = SucursalArea.objects.filter(
                sucursal_piso__sucursal=self.instance
            ).order_by("sucursal_piso__piso", "tipo", "area")
        for form in self.forms:
            if "sucursal_area" in form.fields:
                form.fields["sucursal_area"].queryset = area_qs

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["redes_guardadas"] = self.redes_guardadas
        return kwargs

    def clean(self):
        super().clean()
        if not self.instance or not self.instance.pk:
            return
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            sucursal_area = form.cleaned_data.get("sucursal_area")
            if (
                sucursal_area
                and sucursal_area.sucursal_piso.sucursal_id != self.instance.pk
            ):
                form.add_error("sucursal_area", "El area debe pertenecer a esta sucursal.")


SegmentoRedFormSet = inlineformset_factory(
    Sucursal,
    SegmentoRed,
    form=SegmentoRedForm,
    formset=SegmentoRedFormSetBase,
    extra=1,
    can_delete=True,
)


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

