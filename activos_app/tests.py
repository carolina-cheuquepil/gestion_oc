from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from .views import activos_fijos_list


class ActivosFijosListTests(SimpleTestCase):
    def test_lista_global_de_activos_facturados_a_empresas_internas(self):
        request = RequestFactory().get("/activos/")
        request.session = {}

        queryset = Mock()
        filtrados = queryset.filter.return_value
        distintos = filtrados.distinct.return_value
        ordenados = distintos.order_by.return_value

        with (
            patch("activos_app.views._activos_queryset", return_value=queryset),
            patch("activos_app.views.render") as render,
        ):
            activos_fijos_list.__wrapped__(request)

        filtros = queryset.filter.call_args.kwargs
        self.assertNotIn("sucursal_id", filtros)
        self.assertNotIn("sucursal_id__in", filtros)
        self.assertEqual(
            filtros[
                "recepcion_compra_item__compra_item__ventas_ic__"
                "factura_ic__empresa_receptora_id"
            ].name,
            "sucursal__empresa_id",
        )
        distintos.order_by.assert_called_once_with("sucursal__nombre", "nombre_activo")
        self.assertIs(render.call_args.args[2]["activos"], ordenados)
