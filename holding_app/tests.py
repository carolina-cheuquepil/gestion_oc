from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from .models import Direccion
from .views import sucursal_update


class DireccionTests(SimpleTestCase):
    def test_str_muestra_calle_numero_complemento_y_ciudad(self):
        direccion = Direccion(
            calle="Avenida Siempre Viva",
            numero="742",
            complemento="Departamento 2",
            comuna="Providencia",
            ciudad="Santiago",
            region="Metropolitana",
        )

        self.assertEqual(
            str(direccion),
            "Avenida Siempre Viva, 742, Departamento 2, Santiago",
        )

    def test_str_omite_numero_y_complemento_vacios(self):
        direccion = Direccion(
            calle="Gran Avenida",
            numero="",
            complemento="",
            comuna="San Miguel",
            ciudad="Santiago",
        )

        self.assertEqual(str(direccion), "Gran Avenida, Santiago")


class SucursalUpdateTests(SimpleTestCase):
    @patch("holding_app.views.render")
    @patch("holding_app.views.Direccion.objects.order_by")
    @patch("holding_app.views._save_sucursal_forms")
    @patch("holding_app.views.get_object_or_404")
    def test_edicion_deja_direccion_actual_en_campos_manuales(
        self,
        get_object_or_404_mock,
        save_forms_mock,
        order_by_mock,
        render_mock,
    ):
        holding = Mock(pk=3)
        sucursal = Mock(pk=27, direccion_id=9)
        get_object_or_404_mock.side_effect = [holding, sucursal]
        forms = [Mock() for _ in range(6)]
        save_forms_mock.return_value = (None, *forms)
        order_by_mock.return_value = []
        render_mock.return_value = Mock()

        request = RequestFactory().get("/editar/")
        sucursal_update.__wrapped__(request, empresa_pk=3, pk=27)

        context = render_mock.call_args.args[2]
        self.assertEqual(context["direccion_existente_id"], "")
        self.assertIs(context["direccion_form"], forms[1])
