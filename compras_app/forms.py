#FrontEnd A: Paso 1
from django import forms
from .models import Proveedor, Producto, ProveedorProducto, Compra, CompraItem, FacturaIntercompany, FacturaIntercompanyItem, HistorialCompra
from django.forms import inlineformset_factory
from decimal import Decimal
from django.db.models import Sum
from holding_app.forms import HoldingWidget

# ----------- Proveedores ------------
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

class ProveedorProductoForm(forms.ModelForm):
    class Meta:
        model = ProveedorProducto
        fields = ["proveedor", "uom_compra"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si el proveedor viene como initial, lo bloqueamos
        if self.initial.get("proveedor"):
            self.fields["proveedor"].disabled = True

# ----------- Compras ------------
class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = [
            "tipo_documento","estado_documento","razon_social","proveedor",
            "folio","fecha_emision","fecha_requerida","moneda","observacion",
            "total_neto","total_iva","total",
        ]
        widgets = {
            "fecha_emision": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_requerida": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "observacion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "folio": forms.TextInput(attrs={"class": "form-control"}),
            "total_neto": forms.NumberInput(attrs={"class": "form-control"}),
            "total_iva": forms.NumberInput(attrs={"class": "form-control"}),
            "total": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        total_neto = cleaned_data.get("total_neto") or Decimal("0")
        total_iva = cleaned_data.get("total_iva") or Decimal("0")
        total = cleaned_data.get("total") or Decimal("0")

        if total != (total_neto + total_iva):
            self.add_error("total", "El total debe ser igual a la suma del neto más el IVA.")

        return cleaned_data


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

        # Filtra productos según proveedor (si viene)
        if proveedor:
            self.fields["producto"].queryset = Producto.objects.filter(
                proveedor_productos__proveedor=proveedor
            ).distinct()

    def clean(self):
        
        cleaned = super().clean()

        # Si la fila está vacía (extra), no validar
        if not self.has_changed():
            return cleaned

        # Si está marcada para borrar, no validar
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

CompraItemFormSet = inlineformset_factory(
    Compra,
    CompraItem,
    form=CompraItemForm,
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

            # Si quieres mostrarlos solo lectura en UI, puedes agregar readonly en template
            "total_neto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total_iva": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def clean(self):
        cleaned = super().clean()
        emisora = cleaned.get("empresa_emisora")
        receptora = cleaned.get("empresa_receptora")

        if emisora and receptora and emisora == receptora:
            self.add_error("empresa_receptora", "La empresa receptora debe ser distinta a la emisora.")

        recargo = cleaned.get("recargo_porcentaje")
        if recargo is not None and recargo < 0:
            self.add_error("recargo_porcentaje", "El recargo no puede ser negativo.")

        # Opcional: forzar 5% fijo
        # cleaned["recargo_porcentaje"] = Decimal("5.00")

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
        """
        compra_origen: id de Compra (int) o instancia Compra.
        Filtra compra_item para que el usuario solo pueda escoger ítems de esa compra.
        """
        super().__init__(*args, **kwargs)

        if compra_origen:
            compra_id = getattr(compra_origen, "pk", compra_origen)
            self.fields["compra_item"].queryset = CompraItem.objects.filter(
                compra_id=compra_id
            ).select_related("producto").order_by("nro_linea")

    def clean(self):
        cleaned = super().clean()

        # Filas vacías del formset
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

        # Validar saldo disponible (para evitar sobreventa)
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


class CotizacionUploadForm(forms.ModelForm):
    fecha_documento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = HistorialCompra
        fields = ["fecha_documento", "folio", "archivo"]





