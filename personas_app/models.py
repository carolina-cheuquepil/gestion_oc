from django.db import models
from django.core.validators import RegexValidator

telefono_validator = RegexValidator(
    regex=r"^[0-9+\s()-]{6,20}$",
    message="Teléfono inválido.",
)

class Persona(models.Model):
    persona_id = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=100)
    email = models.EmailField(max_length=120, null=True, blank=True)

    celular = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[telefono_validator],
    )

    class Meta:
        db_table = "persona"
        indexes = [
            models.Index(fields=["apellidos", "nombres"]),
        ]

