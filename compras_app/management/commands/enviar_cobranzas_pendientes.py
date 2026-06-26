from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from compras_app.models import HistorialCompra
from compras_app.views import enviar_correo_cobranza_factura


class Command(BaseCommand):
    help = "Envia correos de cobranza que estaban en espera y ya llegaron a su fecha programada."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        pendientes = (
            HistorialCompra.objects
            .select_related("compra", "tipo_documento", "estado_documento")
            .filter(
                tipo_documento__codigo="EMAIL",
                estado_documento__nombre__iexact="En espera",
                fecha_documento__lte=hoy,
            )
            .order_by("fecha_documento", "historial_compra_id")
        )

        enviados = 0
        omitidos = 0
        fallidos = 0

        for pendiente in pendientes:
            compra = pendiente.compra
            if HistorialCompra.objects.filter(
                compra=compra,
                tipo_documento__codigo="EMAIL",
                estado_documento__nombre__iexact="Cobrado",
            ).exists():
                omitidos += 1
                continue

            factura = (
                HistorialCompra.objects
                .filter(compra=compra, tipo_documento__codigo="FACT")
                .filter(folio=pendiente.folio)
                .order_by("-fecha_evento", "-historial_compra_id")
                .first()
            ) or (
                HistorialCompra.objects
                .filter(compra=compra, tipo_documento__codigo="FACT")
                .order_by("-fecha_evento", "-historial_compra_id")
                .first()
            )

            if not factura:
                omitidos += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Compra {compra.pk}: omitida, no se encontro factura asociada."
                    )
                )
                continue

            with transaction.atomic():
                enviado, error = enviar_correo_cobranza_factura(
                    compra,
                    factura,
                    pendiente.fecha_documento,
                )

            if enviado:
                enviados += 1
                self.stdout.write(self.style.SUCCESS(f"Compra {compra.pk}: cobranza enviada."))
            else:
                fallidos += 1
                self.stdout.write(self.style.ERROR(f"Compra {compra.pk}: {error}"))

        self.stdout.write(
            f"Resultado: {enviados} enviadas, {omitidos} omitidas, {fallidos} fallidas."
        )
