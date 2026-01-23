#FrontEnd: Paso 1
from django import forms
from .models import Persona

class PersonaForm(forms.ModelForm):

    class Meta:
        model = Persona
        fields = ["persona_id", "nombres", "apellidos", "email", "celular"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"
