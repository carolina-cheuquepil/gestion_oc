from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase
from django.template.loader import render_to_string

from .forms import CompraForm
from .views import (
    _redirect_compra_creada,
    _ordenar_compras,
    compra_delete,
    compra_detail,
    facturas_ic_frontend,
    proyecto_create_ajax,
)


class CompraCreateRedirectTests(SimpleTestCase):
    def test_redirige_a_factura_si_compra_inicia_con_factura(self):
        response = _redirect_compra_creada(
            SimpleNamespace(pk=12),
            CompraForm.INICIO_FACTURA,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/compras/compras/ui/12/factura/")

    def test_redirige_al_formulario_normal_si_compra_inicia_con_cotizacion(self):
        response = _redirect_compra_creada(
            SimpleNamespace(pk=12),
            CompraForm.INICIO_COTIZACION,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/compras/compras/ui/12/editar/")


class ComprasOrdenTests(SimpleTestCase):
    @staticmethod
    def compra(compra_id, fecha, estado, proveedor="Proveedor"):
        historial = None
        if fecha is not None or estado is not None:
            historial = SimpleNamespace(
                fecha_documento=fecha,
                estado_documento=estado,
            )
        return SimpleNamespace(
            compra_id=compra_id,
            fecha_emision=date(2026, 1, compra_id),
            proveedor=proveedor,
            ultimo_historial=historial,
        )

    def test_ordena_fecha_descendente_y_deja_fechas_vacias_al_final(self):
        compras = [
            self.compra(1, date(2026, 1, 10), "En espera"),
            self.compra(2, None, "Aprobado"),
            self.compra(3, date(2026, 2, 20), "Pagado"),
        ]

        resultado = _ordenar_compras(compras, "fecha_desc")

        self.assertEqual([compra.compra_id for compra in resultado], [3, 1, 2])

    def test_ordena_fecha_ascendente_y_deja_fechas_vacias_al_final(self):
        compras = [
            self.compra(1, date(2026, 1, 10), "En espera"),
            self.compra(2, None, "Aprobado"),
            self.compra(3, date(2026, 2, 20), "Pagado"),
        ]

        resultado = _ordenar_compras(compras, "fecha_asc")

        self.assertEqual([compra.compra_id for compra in resultado], [1, 3, 2])

    def test_ordena_estado_sin_distinguir_mayusculas(self):
        compras = [
            self.compra(1, date(2026, 1, 10), "Pagado"),
            self.compra(2, date(2026, 1, 11), "aprobado"),
            self.compra(3, None, None),
        ]

        resultado = _ordenar_compras(compras, "estado_asc")

        self.assertEqual([compra.compra_id for compra in resultado], [2, 1, 3])


class CompraRowTests(SimpleTestCase):
    def test_muestra_aprobar_oc_si_tiene_factura_y_no_esta_aprobada(self):
        estado = SimpleNamespace(nombre="Recibido")
        compra = SimpleNamespace(
            compra_id=7,
            ultimo_historial=SimpleNamespace(
                tipo_documento="Factura Proveedor",
                fecha_evento=datetime(2026, 7, 10, 9, 30),
                folio="F-123",
                fecha_documento=date(2026, 7, 10),
                estado_documento=estado,
            ),
            razon_social="Dimarsa",
            proveedor="Proveedor",
            folio="OC-7",
            oc_enviada=False,
            factura_registrada=True,
            oc_aprobada=False,
            estado_documento=estado,
            cobranza_pendiente=False,
            cobranza_pendiente_historial=None,
            contabilidad_ingresada=False,
            pago_registrado=False,
        )

        html = render_to_string("compras_app/_compra_row.html", {"c": compra})

        self.assertIn("Aprobar OC", html)
        self.assertIn('data-pk="7"', html)


class CompraDetailTests(SimpleTestCase):
    @patch("compras_app.views._sincronizar_compra_con_historial")
    @patch("compras_app.views.render")
    @patch("compras_app.views.get_object_or_404")
    def test_muestra_la_factura_clp_mas_reciente(
        self,
        get_object_or_404,
        render,
        sincronizar,
    ):
        factura_anterior = Mock(
            tipo_documento=Mock(codigo="FACT"),
            factura_total_clp=900000,
        )
        factura_reciente = Mock(
            tipo_documento=Mock(codigo="FACT"),
            factura_total_clp=950000,
        )
        otro_documento = Mock(
            tipo_documento=Mock(codigo="OC"),
            factura_total_clp=None,
        )
        compra = get_object_or_404.return_value
        compra.historial.all.return_value = [
            factura_reciente,
            otro_documento,
            factura_anterior,
        ]
        request = RequestFactory().get("/compras/compras/ui/4/")

        compra_detail.__wrapped__(request, 4)

        sincronizar.assert_called_once_with(compra)
        contexto = render.call_args.args[2]
        self.assertIs(contexto["factura_clp"], factura_reciente)


class CompraDeleteTests(SimpleTestCase):
    @patch("compras_app.views.render")
    @patch("compras_app.views.get_object_or_404")
    def test_get_muestra_confirmacion(self, get_object_or_404, render):
        compra = get_object_or_404.return_value
        request = RequestFactory().get("/compras/compras/ui/7/eliminar/")

        compra_delete.__wrapped__(request, 7)

        render.assert_called_once_with(
            request,
            "compras_app/compra_confirm_delete.html",
            {"compra": compra},
        )

    @patch("compras_app.views.messages.success")
    @patch("compras_app.views.get_object_or_404")
    def test_post_elimina_y_redirige_a_lista(self, get_object_or_404, success):
        compra = get_object_or_404.return_value
        compra.pk = 7
        request = RequestFactory().post("/compras/compras/ui/7/eliminar/")

        response = compra_delete.__wrapped__(request, 7)

        compra.delete.assert_called_once_with()
        success.assert_called_once_with(request, "Compra #7 eliminada.")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/compras/compras/ui/")


class FacturasIntercompanyListTests(SimpleTestCase):
    def test_agrupa_facturas_por_folio_y_empresas(self):
        request = RequestFactory().get("/compras/distribucion/ui/")
        request.session = {}

        valores = Mock()
        agrupadas = valores.annotate.return_value
        ordenadas = agrupadas.order_by.return_value

        with (
            patch(
                "compras_app.views.FacturaIntercompany.objects.values",
                return_value=valores,
            ) as values,
            patch("compras_app.views.render") as render,
        ):
            facturas_ic_frontend.__wrapped__(request)

        campos = values.call_args.args
        self.assertIn("folio", campos)
        self.assertIn("compra_origen__proveedor__nombre", campos)
        self.assertIn("empresa_emisora_id", campos)
        self.assertIn("empresa_receptora_id", campos)
        self.assertIn("moneda_id", campos)
        self.assertIn("total", valores.annotate.call_args.kwargs)
        self.assertIs(render.call_args.args[2]["facturas"], ordenadas)


class ProyectoCreateAjaxTests(SimpleTestCase):
    @patch("compras_app.views.ProyectoForm")
    def test_crea_proyecto_y_responde_json(self, proyecto_form):
        proyecto = Mock(pk=18, proyecto_nombre="Renovacion servidores")
        form = proyecto_form.return_value
        form.is_valid.return_value = True
        form.save.return_value = proyecto
        request = RequestFactory().post(
            "/compras/proyectos/nuevo/ajax/",
            {"proyecto_nombre": proyecto.proyecto_nombre, "activo": "on"},
        )

        response = proyecto_create_ajax.__wrapped__(request)

        self.assertEqual(response.status_code, 201)
        self.assertJSONEqual(
            response.content,
            {
                "ok": True,
                "proyecto_id": 18,
                "proyecto_nombre": "Renovacion servidores",
            },
        )
        proyecto_form.assert_called_once_with(request.POST)
        form.save.assert_called_once_with()

    def test_rechaza_metodo_get(self):
        request = RequestFactory().get("/compras/proyectos/nuevo/ajax/")

        response = proyecto_create_ajax.__wrapped__(request)

        self.assertEqual(response.status_code, 405)
