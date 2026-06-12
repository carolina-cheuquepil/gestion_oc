#FrontEnd A: Paso 1
from django import forms
from .models import Compra, CompraItem, FacturaIntercompany, FacturaIntercompanyItem, HistorialCompra, TipoOC, ProyectoInformatica
from proveedores_app.models import Producto
from django.forms import BaseInlineFormSet, inlineformset_factory
from decimal import Decimal
from django.db.models import Sum
from holding_app.forms import HoldingWidget
from proveedores_app.forms import ProveedorWidget

# ----------- Compras ------------
class CompraForm(forms.ModelForm):
    folio_cotizacion = forms.CharField(
        required=False,
        label="Folio cotización",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    fecha_cotizacion = forms.DateField(
        required=False,
        label="Fecha cotización",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    class Meta:
        model = Compra
        fields = [
            "tipo_oc","estado_documento","razon_social","proveedor",
            "folio","fecha_emision","fecha_requerida","moneda","observacion",
        ]
        widgets = {
            "tipo_oc": forms.Select(attrs={"class": "form-select", "id": "id_tipo_oc"}),
            "razon_social": HoldingWidget(attrs={"class": "form-control", "style": "width: 100%;", "data-placeholder": "Buscar por nombre o código..."}),
            "proveedor": ProveedorWidget(attrs={"class": "form-control", "style": "width: 100%;", "data-placeholder": "Buscar por RUT o razón social..."}),
            "fecha_emision": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_requerida": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "observacion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "folio": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folio"].label = "Folio OC"
        self.fields["fecha_emision"].label = "Fecha OC"
        self.fields["estado_documento"].label = "Estado compra"


class CompraItemForm(forms.ModelForm):
    class Meta:
        model = CompraItem
        fields = [
            "nro_linea",
            "producto",
            "descripcion_libre",
            "cantidad",
            "precio_unitario",
            "descuento_porcentaje",
            "afecta_iva",
        ]
        widgets = {
            "nro_linea": forms.NumberInput(attrs={"class": "form-control"}),
            "descripcion_libre": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "descuento_porcentaje": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, proveedor=None, **kwargs):
        super().__init__(*args, **kwargs)

        if proveedor:
            self.fields["producto"].queryset = Producto.objects.filter(
                proveedor_productos__proveedor=proveedor
            ).distinct()

    def clean(self):
        cleaned = super().clean()

        if not self.has_changed():
            return cleaned

        if cleaned.get("DELETE"):
            return cleaned

        producto = cleaned.get("producto")
        desc = (cleaned.get("descripcion_libre") or "").strip()

        if not producto and not desc:
            self.add_error("producto", "Selecciona un producto o escribe una descripción.")
            self.add_error("descripcion_libre", "Selecciona un producto o escribe una descripción.")

        if producto and desc:
            self.add_error("descripcion_libre", "Si eliges un producto, no uses descripción libre.")

        return cleaned

class CompraItemBaseFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        tiene_items = False
        for form in self.forms:
            if not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("producto") or form.cleaned_data.get("descripcion_libre"):
                tiene_items = True
                break

        if not tiene_items:
            raise forms.ValidationError("Agrega al menos un item a la compra.")


CompraItemFormSet = inlineformset_factory(
    Compra,
    CompraItem,
    form=CompraItemForm,
    formset=CompraItemBaseFormSet,
    fields=[
        "producto",
        "descripcion_libre",
        "cantidad",
        "precio_unitario",
        "descuento_porcentaje",
        "afecta_iva",
    ],
    extra=0,
    can_delete=True,
)

# ----------- Distribución interna ------------
class FacturaIntercompanyForm(forms.ModelForm):
    class Meta:
        model = FacturaIntercompany
        fields = [
            "empresa_emisora",
            "empresa_receptora",
            "compra_origen",
            "folio",
            "fecha_emision",
            "moneda",
            "recargo_porcentaje",
            "total_neto",
            "total_iva",
            "total",
        ]
        widgets = {
            "empresa_emisora": forms.Select(attrs={"class": "form-control"}),
            "empresa_receptora": forms.Select(attrs={"class": "form-control"}),
            "compra_origen": forms.Select(attrs={"class": "form-control"}),
            "folio": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_emision": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "moneda": forms.Select(attrs={"class": "form-control"}),
            "recargo_porcentaje": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total_neto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total_iva": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        emisora = cleaned.get("empresa_emisora")
        receptora = cleaned.get("empresa_receptora")

        if emisora and receptora and emisora == receptora:
            self.add_error("empresa_receptora", "La empresa receptora debe ser distinta a la emisora.")

        recargo = cleaned.get("recargo_porcentaje")
        if recargo is not None and recargo < 0:
            self.add_error("recargo_porcentaje", "El recargo no puede ser negativo.")

        return cleaned

class FacturaIntercompanyItemForm(forms.ModelForm):
    class Meta:
        model = FacturaIntercompanyItem
        fields = [
            "compra_item",
            "cantidad",
            "afecta_iva",
        ]
        widgets = {
            "compra_item": forms.Select(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "afecta_iva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, compra_origen=None, **kwargs):
        super().__init__(*args, **kwargs)

        if compra_origen:
            compra_id = getattr(compra_origen, "pk", compra_origen)
            self.fields["compra_item"].queryset = CompraItem.objects.filter(
                compra_id=compra_id
            ).select_related("producto").order_by("nro_linea")

    def clean(self):
        cleaned = super().clean()

        if not self.has_changed():
            return cleaned

        if cleaned.get("DELETE"):
            return cleaned

        compra_item = cleaned.get("compra_item")
        cantidad = cleaned.get("cantidad") or Decimal("0")

        if not compra_item:
            self.add_error("compra_item", "Selecciona un ítem de la compra.")
            return cleaned

        if cantidad <= 0:
            self.add_error("cantidad", "La cantidad debe ser mayor a 0.")
            return cleaned

        vendido = (
            FacturaIntercompanyItem.objects
            .filter(compra_item=compra_item)
            .exclude(pk=self.instance.pk)
            .aggregate(s=Sum("cantidad"))["s"] or Decimal("0")
        )
        disponible = (compra_item.cantidad or Decimal("0")) - vendido

        if cantidad > disponible:
            self.add_error("cantidad", f"La cantidad excede el saldo disponible. Disponible: {disponible}")

        return cleaned


FacturaIntercompanyItemFormSet = inlineformset_factory(
    FacturaIntercompany,
    FacturaIntercompanyItem,
    form=FacturaIntercompanyItemForm,
    fields=[
        "compra_item",
        "cantidad",
        "afecta_iva",
    ],
    extra=1,
    can_delete=True,
)


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = ProyectoInformatica
        fields = ["proyecto_nombre", "fecha_inicio", "fecha_fin", "activo"]
        widgets = {
            "proyecto_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CotizacionUploadForm(forms.ModelForm):
    fecha_documento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = HistorialCompra
        fields = ["fecha_documento", "folio", "archivo"]


class FacturaProveedorForm(forms.Form):
    fecha_factura = forms.DateField(
        required=False,
        label="Fecha factura recibida",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    folio_factura = forms.CharField(
        required=False,
        max_length=30,
        label="Folio factura",
        widget=forms.TextInput(attrs={"class": "form-control", "maxlength": 30}),
    )
    observacion_factura = forms.CharField(
        required=False,
        label="Observación",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def clean(self):
        cleaned_data = super().clean()
        fecha_factura = cleaned_data.get("fecha_factura")
        folio_factura = (cleaned_data.get("folio_factura") or "").strip()
        if fecha_factura and not folio_factura:
            self.add_error("folio_factura", "Debes ingresar el folio de la factura.")
        if folio_factura and not fecha_factura:
            self.add_error("fecha_factura", "Debes ingresar la fecha de la factura.")
        cleaned_data["folio_factura"] = folio_factura
        return cleaned_data
