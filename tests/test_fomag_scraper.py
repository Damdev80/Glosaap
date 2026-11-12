"""
Tests para el scraper de Fomag (fomag_scraper.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del scraper
- Configuración de navegadores
- Procesos de login y descarga
- Manejo de errores y timeouts
- Configuración de perfiles de navegador
"""
import os
from unittest.mock import MagicMock, call, patch

import pytest

from app.service.web_scraper.base_scraper import BaseScraper
from app.service.web_scraper.fomag_scraper import FomagScraper


class TestFomagScraperImport:
    """Tests para importación del módulo."""

    def test_module_import(self):
        """Puede importar el módulo"""
        from app.service.web_scraper import fomag_scraper
        assert fomag_scraper is not None

    def test_fomag_scraper_class(self):
        """FomagScraper está definido"""
        assert FomagScraper is not None


class TestFomagScraperInheritance:
    """Tests para herencia de clase."""

    def test_inherits_from_base_scraper(self):
        """FomagScraper hereda de BaseScraper"""
        assert issubclass(FomagScraper, BaseScraper)


class TestFomagScraperInit:
    """Tests para inicialización del scraper."""

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_creation(self, mock_makedirs, mock_ensure):
        """Crea el scraper correctamente"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert scraper is not None
        assert scraper.url is not None

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_has_horus_url(self, mock_makedirs, mock_ensure):
        """Tiene URL del portal Horus"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert "horus" in scraper.url.lower()
        assert scraper.url.startswith("https://")

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_profile_directory_creation(self, mock_makedirs, mock_ensure):
        """Crea directorio de perfil automáticamente"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert scraper.perfil_dir is not None
        mock_makedirs.assert_called()

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_custom_profile_dir(self, mock_makedirs, mock_ensure):
        """Acepta directorio de perfil personalizado"""
        custom_profile = "/custom/profile"
        scraper = FomagScraper(download_dir="/tmp/test", perfil_dir=custom_profile)
        # En Windows, os.path.abspath convierte /custom/profile a C:\custom\profile
        assert "custom" in scraper.perfil_dir and "profile" in scraper.perfil_dir

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('sys.platform', 'win32')
    def test_scraper_windows_profile_path(self, mock_makedirs, mock_ensure):
        """Usa AppData en Windows para perfil"""
        with patch.dict('os.environ', {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
            scraper = FomagScraper(download_dir="/tmp/test")
            assert 'AppData' in scraper.perfil_dir or 'Glosaap' in scraper.perfil_dir


class TestFomagScraperBrowserSetup:
    """Tests para configuración de navegadores."""

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_ensure_browsers_finds_chromium(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Encuentra Chromium instalado correctamente"""
        # Mock browser path exists
        mock_exists.return_value = True
        mock_listdir.return_value = ['chromium-12345', 'firefox-67890']

        scraper = FomagScraper.__new__(FomagScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        scraper.perfil_dir = "/tmp/profile"

        # Should not raise exception
        scraper._ensure_playwright_browsers()

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_ensure_browsers_fallback_to_direct_launch(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Test fallback cuando no encuentra navegadores en path"""
        # Mock no browsers found in path
        mock_exists.return_value = False

        # Mock successful playwright launch
        mock_browser = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        scraper = FomagScraper.__new__(FomagScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        scraper.perfil_dir = "/tmp/profile"

        # Should not raise exception
        scraper._ensure_playwright_browsers()

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_ensure_browsers_installation_error(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Test error cuando Playwright no está instalado"""
        # Mock no browsers found
        mock_exists.return_value = False

        # Mock playwright failure
        mock_playwright.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("Browser not found")

        scraper = FomagScraper.__new__(FomagScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        scraper.perfil_dir = "/tmp/profile"

        with pytest.raises(Exception, match="Navegadores no instalados"):
            scraper._ensure_playwright_browsers()

    @patch.dict('os.environ', {}, clear=True)
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_browsers_path_auto_configuration(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Test configuración automática de PLAYWRIGHT_BROWSERS_PATH"""
        # Mock environment
        mock_exists.return_value = True
        mock_listdir.return_value = ['chromium-12345']

        scraper = FomagScraper.__new__(FomagScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        scraper.perfil_dir = "/tmp/profile"

        scraper._ensure_playwright_browsers()

        # Should set environment variable
        assert 'PLAYWRIGHT_BROWSERS_PATH' in os.environ

    @patch('app.service.web_scraper.fomag_scraper.find_system_browser')
    @patch('os.path.exists', return_value=False)
    def test_ensure_browsers_uses_system_chrome_or_edge(self, mock_exists, mock_sys_browser):
        """Usa Chrome o Edge del sistema si no hay Chromium descargado en AppData"""
        mock_sys_browser.return_value = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

        scraper = FomagScraper.__new__(FomagScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        scraper.perfil_dir = "/tmp/profile"

        scraper._ensure_playwright_browsers()

        assert scraper.executable_path == r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


class TestFechasInformePrestador:
    """Validación y división de rangos (el portal limita a 14 días)."""

    def test_parse_fecha_formatos(self):
        from datetime import date

        from app.service.web_scraper.fomag_scraper import parse_fecha

        esperado = date(2026, 3, 5)
        assert parse_fecha("2026-03-05") == esperado
        assert parse_fecha("2026/03/05") == esperado
        assert parse_fecha("05/03/2026") == esperado
        assert parse_fecha(esperado) == esperado

    def test_parse_fecha_invalida(self):
        from app.service.web_scraper.fomag_scraper import parse_fecha

        with pytest.raises(ValueError):
            parse_fecha("no-es-fecha")
        with pytest.raises(ValueError):
            parse_fecha("")

    def test_rango_corto_un_solo_tramo(self):
        from datetime import date

        from app.service.web_scraper.fomag_scraper import dividir_rango_fechas

        assert dividir_rango_fechas(date(2026, 1, 1), date(2026, 1, 14)) == [
            (date(2026, 1, 1), date(2026, 1, 14))
        ]
        assert dividir_rango_fechas(date(2026, 1, 5), date(2026, 1, 5)) == [
            (date(2026, 1, 5), date(2026, 1, 5))
        ]

    def test_rango_largo_se_divide_en_tramos_de_14_dias(self):
        from datetime import date, timedelta

        from app.service.web_scraper.fomag_scraper import (
            MAX_DIAS_RANGO,
            dividir_rango_fechas,
        )

        desde, hasta = date(2026, 1, 1), date(2026, 3, 1)  # 60 días
        tramos = dividir_rango_fechas(desde, hasta)
        assert len(tramos) == 5
        assert tramos[0][0] == desde and tramos[-1][1] == hasta
        for ini, fin in tramos:
            assert (fin - ini).days + 1 <= MAX_DIAS_RANGO
        # Consecutivos, sin huecos ni solapes
        for (_, fin), (ini_sig, _) in zip(tramos, tramos[1:], strict=False):
            assert ini_sig == fin + timedelta(days=1)

    def test_rango_invertido_falla(self):
        from datetime import date

        from app.service.web_scraper.fomag_scraper import dividir_rango_fechas

        with pytest.raises(ValueError):
            dividir_rango_fechas(date(2026, 2, 1), date(2026, 1, 1))


def _scraper(tmp_path):
    with patch.object(FomagScraper, '_ensure_playwright_browsers'):
        return FomagScraper(
            download_dir=str(tmp_path / "out"), perfil_dir=str(tmp_path / "perfil")
        )


def _mock_playwright(mock_playwright, page, descarga_nombre="informe.xlsx"):
    context = MagicMock()
    context.pages = [page]
    mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = context
    download = MagicMock()
    download.suggested_filename = descarga_nombre
    page.expect_download.return_value.__enter__.return_value.value = download
    return context, download


@patch('app.service.web_scraper.fomag_scraper.time.sleep')
@patch('app.service.web_scraper.fomag_scraper.sync_playwright')
class TestFomagInformePrestador:
    """Flujo Cuentas médicas -> Informe prestador con filtros y tramos."""

    def test_rango_largo_descarga_un_excel_por_tramo(self, mock_playwright, _sleep, tmp_path):
        page = MagicMock()
        page.query_selector.return_value = None  # sesión activa
        context, _ = _mock_playwright(mock_playwright, page)
        scraper = _scraper(tmp_path)

        result = scraper.login_and_download("u", "p", "2026-01-01", "2026-03-01")

        assert result["success"] is True
        assert result["tramos"] == 5
        assert result["files"] == 5
        assert result["fallidos"] == []
        assert page.expect_download.call_count == 5
        page.fill.assert_not_called()  # sesión activa: no se llena login
        page.click.assert_any_call('a[href="/cuentasMedicas/informePrestador"]')
        page.wait_for_selector.assert_any_call(
            ".v-list-group__header:has(.mdi-bank)", timeout=180_000
        )
        context.close.assert_called_once()

    def test_nombre_de_archivo_por_tramo(self, mock_playwright, _sleep, tmp_path):
        page = MagicMock()
        page.query_selector.return_value = None
        _, download = _mock_playwright(mock_playwright, page)
        scraper = _scraper(tmp_path)

        scraper.login_and_download("u", "p", "2026-01-01", "2026-01-10")

        ruta = download.save_as.call_args[0][0]
        assert os.path.basename(ruta) == "fomag_trazabilidad_20260101_20260110.xlsx"

    def test_tramo_sin_descarga_no_aborta_los_demas(self, mock_playwright, _sleep, tmp_path):
        from playwright.sync_api import TimeoutError as PWTimeout

        page = MagicMock()
        page.query_selector.return_value = None
        _mock_playwright(mock_playwright, page)
        ok = page.expect_download.return_value
        # El 2.º tramo no genera descarga (timeout); el resto sí.
        page.expect_download.side_effect = [ok, PWTimeout("timeout"), ok]
        scraper = _scraper(tmp_path)

        result = scraper.login_and_download("u", "p", "2026-01-01", "2026-02-02")  # 33 días -> 3 tramos

        assert result["success"] is True
        assert result["files"] == 2
        assert len(result["fallidos"]) == 1
        assert "Sin descarga" in result["message"]

    def test_sin_ninguna_descarga_falla(self, mock_playwright, _sleep, tmp_path):
        from playwright.sync_api import TimeoutError as PWTimeout

        page = MagicMock()
        page.query_selector.return_value = None
        _mock_playwright(mock_playwright, page)
        page.expect_download.side_effect = PWTimeout("timeout")
        scraper = _scraper(tmp_path)

        result = scraper.login_and_download("u", "p", "2026-01-01", "2026-01-05")

        assert result["success"] is False
        assert result["files"] == 0

    def test_login_llena_credenciales_y_espera_captcha_manual(self, mock_playwright, _sleep, tmp_path):
        page = MagicMock()
        page.query_selector.return_value = MagicMock()  # formulario de login
        _mock_playwright(mock_playwright, page)
        scraper = _scraper(tmp_path)

        scraper.login_and_download("usuario", "clave", "2026-01-01", "2026-01-05")

        page.fill.assert_any_call('input[id="input-15"]', "usuario")
        page.fill.assert_any_call('input[id="input-19"]', "clave")
        # El submit lo hace el usuario tras el CAPTCHA: no se hace click automático
        assert call('button[type="submit"]') not in page.click.call_args_list

    def test_rango_invalido_no_abre_navegador(self, mock_playwright, _sleep, tmp_path):
        scraper = _scraper(tmp_path)

        invertido = scraper.login_and_download("u", "p", "2026-02-01", "2026-01-01")
        incompleto = scraper.login_and_download("u", "p", "2026-02-01", None)
        texto = scraper.login_and_download("u", "p", "xx", "yy")

        for r in (invertido, incompleto, texto):
            assert r["success"] is False
            assert "error" in r["message"].lower()
        mock_playwright.assert_not_called()

    def test_sin_fechas_usa_ultimos_14_dias(self, mock_playwright, _sleep, tmp_path):
        page = MagicMock()
        page.query_selector.return_value = None
        _mock_playwright(mock_playwright, page)
        scraper = _scraper(tmp_path)

        result = scraper.login_and_download("u", "p")

        assert result["tramos"] == 1
        assert result["files"] == 1

    def test_error_de_navegador_retorna_error(self, mock_playwright, _sleep, tmp_path):
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.side_effect = Exception("Navigation failed")
        scraper = _scraper(tmp_path)

        result = scraper.login_and_download("u", "p", "2026-01-01", "2026-01-05")

        assert result["success"] is False
        assert "error" in result["message"].lower()


class TestFomagScraperMetadata:
    def test_method_signatures(self):
        import inspect

        params = list(inspect.signature(FomagScraper.login_and_download).parameters)
        for nombre in ("usuario", "contraseña", "fecha_desde", "fecha_hasta"):
            assert nombre in params

        init_params = list(inspect.signature(FomagScraper.__init__).parameters)
        for nombre in ("download_dir", "progress_callback", "perfil_dir"):
            assert nombre in init_params

    def test_class_doc_menciona_fomag(self):
        assert FomagScraper.__doc__ is not None
        assert 'Fomag' in FomagScraper.__doc__ or 'Horus' in FomagScraper.__doc__
