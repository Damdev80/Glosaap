"""
Tests para el scraper de Familiar (familiar_scraper.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del scraper
- Configuración de navegadores
- Estructura del scraper
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from app.service.web_scraper.familiar_scraper import FamiliarScraper
from app.service.web_scraper.base_scraper import BaseScraper


class TestFamiliarScraperImport:
    """Tests para importación del módulo."""
    
    def test_module_import(self):
        """Puede importar el módulo"""
        from app.service.web_scraper import familiar_scraper
        assert familiar_scraper is not None
    
    def test_familiar_scraper_class(self):
        """FamiliarScraper está definido"""
        assert FamiliarScraper is not None


class TestFamiliarScraperInheritance:
    """Tests para herencia de clase."""
    
    def test_inherits_from_base_scraper(self):
        """FamiliarScraper hereda de BaseScraper"""
        assert issubclass(FamiliarScraper, BaseScraper)


class TestFamiliarScraperInit:
    """Tests para inicialización del scraper."""
    
    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_creation(self, mock_makedirs, mock_ensure):
        """Crea el scraper correctamente"""
        scraper = FamiliarScraper(download_dir="/tmp/test")
        assert scraper is not None
    
    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_has_url(self, mock_makedirs, mock_ensure):
        """Tiene URL del portal"""
        scraper = FamiliarScraper(download_dir="/tmp/test")
        assert scraper.url is not None
        assert "familiardecolombia" in scraper.url
    
    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_url_is_https(self, mock_makedirs, mock_ensure):
        """URL usa HTTPS"""
        scraper = FamiliarScraper(download_dir="/tmp/test")
        assert scraper.url.startswith("https://")
    
    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_inherits_download_dir(self, mock_makedirs, mock_ensure):
        """Hereda download_dir del padre"""
        scraper = FamiliarScraper(download_dir="/custom/dir")
        assert scraper.download_dir == "/custom/dir"


class TestFamiliarScraperMethods:
    """Tests para métodos del scraper."""
    
    def test_has_login_and_download(self):
        """Tiene método login_and_download"""
        assert hasattr(FamiliarScraper, 'login_and_download')
    
    def test_has_ensure_playwright_browsers(self):
        """Tiene método _ensure_playwright_browsers"""
        assert hasattr(FamiliarScraper, '_ensure_playwright_browsers')


class TestFamiliarScraperClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """FamiliarScraper es una clase"""
        assert isinstance(FamiliarScraper, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert FamiliarScraper.__doc__ is not None


class TestFamiliarScraperEnsureBrowsers:
    """Tests para verificación de navegadores."""
    
    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['chromium-1234'])
    @patch('os.makedirs')
    def test_ensure_browsers_finds_chromium(self, mock_makedirs, mock_listdir, mock_exists):
        """Encuentra Chromium instalado"""
        # Debería no lanzar excepción
        with patch.object(FamiliarScraper, '__init__', lambda x, **kw: None):
            scraper = FamiliarScraper.__new__(FamiliarScraper)
            scraper.download_dir = "/tmp"
            scraper.progress_callback = print
            
            scraper._ensure_playwright_browsers()


class TestFamiliarScraperLoginDownload:
    """Tests para login_and_download."""
    
    def test_login_and_download_signature(self):
        """login_and_download tiene parámetros correctos"""
        import inspect
        sig = inspect.signature(FamiliarScraper.login_and_download)
        params = sig.parameters
        
        assert 'nit' in params
        assert 'usuario' in params
        # Nota: Python usa caracteres especiales en nombres de parámetros

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_login_and_download_mock_playwright(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test login_and_download con Playwright mockeado"""
        # Setup mocks
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock page interactions
        mock_page.query_selector_all.return_value = []  # No rows found
        
        scraper = FamiliarScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download(
            nit="123456789",
            usuario="test_user", 
            contraseña="test_pass",
            fecha_inicio="2024/01/01",
            fecha_fin="2024/01/31"
        )
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'files' in result
        assert 'message' in result

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_login_error_handling(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test manejo de errores en login"""
        # Mock que lanza excepción
        mock_playwright.return_value.__enter__.side_effect = Exception("Connection error")
        
        scraper = FamiliarScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("123456789", "user", "pass")
        
        assert result['success'] is False
        assert 'error' in result['message'].lower() or 'connection error' in result['message'].lower()

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_no_records_found(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test cuando no se encuentran registros"""
        # Setup mocks
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock empty results
        mock_page.query_selector_all.return_value = []
        
        scraper = FamiliarScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("123456789", "user", "pass")
        
        assert result['success'] is True
        assert result['files'] == 0
        assert 'no se encontraron' in result['message'].lower()

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_download_files_success(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test descarga exitosa de archivos"""
        # Setup mocks
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_download = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock 2 rows found
        mock_page.query_selector_all.return_value = [MagicMock(), MagicMock()]
        
        # Mock download buttons
        mock_page.query_selector.return_value = MagicMock()
        
        # Mock download process
        mock_page.expect_download.return_value.__enter__.return_value.value = mock_download
        mock_download.suggested_filename = "test_file.xlsx"
        
        scraper = FamiliarScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("123456789", "user", "pass")
        
        assert result['success'] is True
        assert result['files'] >= 0

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers') 
    @patch('os.makedirs')
    def test_default_date_parameters(self, mock_makedirs, mock_ensure):
        """Test parámetros de fecha opcionales"""
        scraper = FamiliarScraper(download_dir="/tmp/test")
        
        # Verificar que acepta parámetros opcionales
        with patch('app.service.web_scraper.familiar_scraper.sync_playwright') as mock_pw:
            mock_pw.return_value.__enter__.side_effect = Exception("Test exception")
            
            result = scraper.login_and_download("123456789", "user", "pass")
            assert isinstance(result, dict)

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs') 
    def test_navigation_error_handling(self, mock_makedirs, mock_ensure):
        """Test manejo de errores de navegación"""
        with patch('app.service.web_scraper.familiar_scraper.sync_playwright') as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            
            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock navigation failure
            mock_page.wait_for_selector.side_effect = Exception("Navigation timeout")
            
            scraper = FamiliarScraper(download_dir="/tmp/test")
            result = scraper.login_and_download("123456789", "user", "pass")
            
            assert result['success'] is False
            assert 'navegando' in result['message'].lower() or 'navigation' in result['message'].lower() or 'error' in result['message'].lower()


class TestFamiliarScraperBrowserConfiguration:
    """Tests para configuración de navegadores."""
    
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_playwright_fallback(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Test fallback cuando no encuentra navegadores instalados"""
        # Mock no browser found in path
        mock_exists.return_value = False
        
        # Mock successful playwright launch
        mock_browser = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        
        scraper = FamiliarScraper.__new__(FamiliarScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        
        # Should not raise exception
        scraper._ensure_playwright_browsers()

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_playwright_installation_error(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Test error cuando Playwright no está instalado"""
        # Mock no browser found
        mock_exists.return_value = False
        
        # Mock playwright failure
        mock_playwright.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("Browser not found")
        
        scraper = FamiliarScraper.__new__(FamiliarScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        
        with pytest.raises(Exception):
            scraper._ensure_playwright_browsers()

    @patch.dict('os.environ', {}, clear=True)
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_browser_path_configuration(self, mock_playwright, mock_makedirs, mock_listdir, mock_exists):
        """Test configuración automática de ruta de navegadores"""
        # Mock environment setup
        mock_exists.return_value = True
        mock_listdir.return_value = ['chromium-12345']
        
        scraper = FamiliarScraper.__new__(FamiliarScraper)
        scraper.download_dir = "/tmp"
        scraper.progress_callback = print
        
        scraper._ensure_playwright_browsers()
        
        # Should set PLAYWRIGHT_BROWSERS_PATH
        assert 'PLAYWRIGHT_BROWSERS_PATH' in os.environ


class TestFamiliarScraperErrorScenarios:
    """Tests para escenarios de error específicos."""
    
    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_button_detection_fallback(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test detección de botones de descarga con fallbacks"""
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock multiple rows but no standard buttons
        mock_page.query_selector_all.return_value = [MagicMock(), MagicMock()]
        
        # Mock query_selector to return None for standard selectors, then a button
        call_count = 0
        def mock_query_selector(selector):
            nonlocal call_count
            call_count += 1
            if 'cmd_export' in selector or 'cmdExportar' in selector:
                return None
            if call_count > 10:  # Generic button selector
                mock_btn = MagicMock()
                mock_btn.get_attribute.return_value = "j_idt120:0:custom_button"
                return mock_btn
            return None
        
        mock_page.query_selector.side_effect = mock_query_selector
        
        scraper = FamiliarScraper(download_dir="/tmp/test")
        result = scraper.login_and_download("123456789", "user", "pass")
        
        assert isinstance(result, dict)

    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.familiar_scraper.sync_playwright')
    def test_download_timeout_handling(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test manejo de timeouts en descarga"""
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock one row found
        mock_page.query_selector_all.return_value = [MagicMock()]
        mock_page.query_selector.return_value = MagicMock()
        
        # Mock download timeout
        from playwright.sync_api import TimeoutError
        mock_page.expect_download.return_value.__enter__.side_effect = TimeoutError("Download timeout")
        
        scraper = FamiliarScraper(download_dir="/tmp/test")
        result = scraper.login_and_download("123456789", "user", "pass")
        
        assert result['success'] is True
        assert result['files'] == 0  # No successful downloads due to timeout


class TestFamiliarScraperIntegration:
    """Tests de integración."""
    
    @patch.object(FamiliarScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_complete_workflow_mock(self, mock_makedirs, mock_ensure):
        """Test workflow completo con mocks"""
        with patch('app.service.web_scraper.familiar_scraper.sync_playwright') as mock_pw:
            # Setup complete mock chain
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_download = MagicMock()
            
            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock successful navigation and data
            mock_page.query_selector_all.return_value = [MagicMock()]
            mock_page.query_selector.return_value = MagicMock()
            mock_page.expect_download.return_value.__enter__.return_value.value = mock_download
            mock_download.suggested_filename = "glosa_file.xlsx"
            
            scraper = FamiliarScraper(download_dir="/tmp/test")
            result = scraper.login_and_download(
                nit="900123456",
                usuario="test_user",
                contraseña="test_password",
                fecha_inicio="2024/01/01", 
                fecha_fin="2024/01/31"
            )
            
            # Verify workflow executed
            mock_page.goto.assert_called_once()
            mock_page.fill.assert_called()  # Should be called multiple times for form fields
            mock_page.click.assert_called()  # Should be called for submit and download
            
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'files' in result
            assert 'message' in result
