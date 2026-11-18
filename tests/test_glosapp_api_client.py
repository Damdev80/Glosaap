"""
Tests unitarios para el cliente de la API REST de Glosaap y el Dashboard Analítico.
"""
from unittest.mock import MagicMock, patch

from app.service.glosapp_api_client import GlosappApiClient
from app.ui.views.analytics_dashboard_view import AnalyticsDashboardView


class TestGlosappApiClient:
    """Pruebas para GlosappApiClient."""

    def test_initialization_and_update(self):
        client = GlosappApiClient(base_url="http://test-server:8000/glosapp/api/v1/", api_key="test-key-123")
        assert client.base_url == "http://test-server:8000/glosapp/api/v1"
        assert client.api_key == "test-key-123"

        client.update_credentials(base_url="http://nuevo:8000/v1/", api_key="nueva-clave")
        assert client.base_url == "http://nuevo:8000/v1"
        assert client.api_key == "nueva-clave"

    @patch("requests.Session.get")
    def test_check_health_ok(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"estado": "ok", "base_datos": "ok"}
        mock_get.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1")
        res = client.check_health()
        assert res["ok"] is True
        assert res["status_code"] == 200
        assert res["data"]["estado"] == "ok"
        mock_get.assert_called_once_with("http://10.10.10.18:8000/glosapp/api/v1/salud", timeout=(2.5, 4.0))

    @patch("requests.Session.get")
    def test_validate_key_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"codigo_eps": "MUTUALSER"}]
        mock_get.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1", api_key="secret-key")
        val = client.validate_key()
        assert val["valid"] is True
        assert val["status_code"] == 200

    @patch("requests.Session.get")
    def test_validate_key_unauthorized(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1", api_key="wrong-key")
        val = client.validate_key()
        assert val["valid"] is False
        assert val["status_code"] == 401
        assert "inválida" in val["message"].lower()

    @patch("requests.Session.get")
    def test_get_lotes(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total": 1,
            "limit": 100,
            "offset": 0,
            "items": [{"id_lote": 1, "codigo_eps": "MUTUALSER", "valor_total_objetado": 500000}],
        }
        mock_get.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1")
        res = client.get_lotes(codigo_eps="MUTUALSER")
        assert res["total"] == 1
        assert len(res["items"]) == 1
        assert res["items"][0]["codigo_eps"] == "MUTUALSER"

    @patch("requests.Session.get")
    def test_get_metricas_resumen(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"modulo": "PROCESADOR", "fase_operacion": "LECTURA_EXCEL", "duracion_promedio_seg": 12.5}
        ]
        mock_get.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1")
        res = client.get_metricas_resumen()
        assert len(res) == 1
        assert res[0]["fase_operacion"] == "LECTURA_EXCEL"

    @patch("requests.Session.post")
    def test_registrar_lote_completo(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"lote": {"id_lote": 42}, "facturas": []}
        mock_post.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1")
        payload = {"codigo_eps": "FOMAG", "origen": "PORTAL_WEB", "facturas": []}
        res = client.registrar_lote_completo(payload)
        assert res["success"] is True
        assert res["data"]["lote"]["id_lote"] == 42
        assert payload["usuario_responsable"] != ""
        assert payload["nombre_equipo"] != ""

    @patch("requests.Session.post")
    def test_abrir_y_cerrar_sesion(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id_sesion": 105}
        mock_post.return_value = mock_resp

        client = GlosappApiClient(base_url="http://10.10.10.18:8000/glosapp/api/v1")
        id_sesion = client.abrir_sesion()
        assert id_sesion == 105

        mock_resp.status_code = 200
        cerrado = client.cerrar_sesion(105)
        assert cerrado is True


class TestAnalyticsDashboardView:
    """Pruebas para la interfaz AnalyticsDashboardView."""

    def test_view_creation(self):
        mock_page = MagicMock()
        mock_page.client_storage = MagicMock()
        mock_page.client_storage.get.return_value = None

        view = AnalyticsDashboardView(page=mock_page)
        assert view.container is not None
        assert view.container.visible is False

        view.show()
        assert view.container.visible is True

        view.hide()
        assert view.container.visible is False

    def test_navigation_back(self):
        mock_page = MagicMock()
        on_back_called = []
        view = AnalyticsDashboardView(page=mock_page, on_back=lambda: on_back_called.append(True))
        view._handle_back()
        assert len(on_back_called) == 1
