"""
Tests para el scraper de Fomag (fomag_scraper.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del scraper
- Configuración de navegadores
- Procesos de login y descarga
- Manejo de errores y timeouts
- Configuración de perfiles de navegador
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from app.service.web_scraper.fomag_scraper import FomagScraper
from app.service.web_scraper.base_scraper import BaseScraper


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
        
        with pytest.raises(Exception):
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


class TestFomagScraperLoginDownload:
    """Tests para función login_and_download."""
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_login_and_download_basic_flow(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test flujo básico de login y descarga"""
        # Setup mocks
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock login form detection
        mock_page.query_selector.return_value = MagicMock()  # Login form found
        
        # Mock Excel icons (empty page)
        mock_page.query_selector_all.return_value = []
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'files' in result
        assert 'message' in result

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_login_with_active_session(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test cuando ya hay sesión activa"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock no login form (session active)
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        # Should not try to fill login form
        mock_page.fill.assert_not_called()
        assert isinstance(result, dict)

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_download_excel_files(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test descarga de archivos Excel"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_download = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock login form and Excel icons
        mock_page.query_selector.return_value = None  # No login needed
        
        # Mock 2 Excel files found
        mock_icon1 = MagicMock()
        mock_icon2 = MagicMock()
        mock_page.query_selector_all.return_value = [mock_icon1, mock_icon2]
        
        # Mock button elements
        mock_button = MagicMock()
        mock_page.evaluate_handle.return_value.as_element.return_value = mock_button
        
        # Mock download process
        mock_page.expect_download.return_value.__enter__.return_value.value = mock_download
        mock_download.suggested_filename = "fomag_file.xlsx"
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        assert result['success'] is True
        assert result['files'] >= 0

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_navigation_error_handling(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test manejo de errores de navegación"""
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.side_effect = Exception("Navigation failed")
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        assert result['success'] is False
        assert 'error' in result['message'].lower() or 'failed' in result['message'].lower()

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_no_excel_files_found(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test cuando no se encuentran archivos Excel"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock no login needed, no Excel files
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        assert result['success'] is False
        assert result['files'] == 0
        assert 'no se encontraron' in result['message'].lower()


class TestFomagScraperPagination:
    """Tests para funcionalidad de paginación."""
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_pagination_configuration(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test configuración de paginación a 100 registros"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock pagination elements
        mock_footer = MagicMock()
        mock_select = MagicMock()
        mock_option_100 = MagicMock()
        
        mock_page.query_selector.side_effect = [
            None,  # No login form
            mock_footer,  # Footer found
            mock_option_100  # Option 100 found
        ]
        mock_footer.query_selector.return_value = mock_select
        
        # Mock no Excel files for quick exit
        mock_page.query_selector_all.return_value = []
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        # Should attempt pagination configuration
        mock_select.click.assert_called()
        mock_option_100.click.assert_called()

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_pagination_fallback(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test fallback cuando paginación falla"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock pagination failure
        mock_page.query_selector.return_value = None  # No footer found
        mock_page.query_selector_all.return_value = []
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        # Should continue without pagination
        assert isinstance(result, dict)


class TestFomagScraperDownloadDetails:
    """Tests para detalles del proceso de descarga."""
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    @patch('os.path.exists')
    def test_duplicate_filename_handling(self, mock_exists, mock_playwright, mock_makedirs, mock_ensure):
        """Test manejo de nombres duplicados"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_download = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock: archivo existe solo las primeras 2 veces, luego no existe
        mock_exists.side_effect = [True, True, False]
        
        # Mock Excel file found
        mock_icon = MagicMock()
        mock_page.query_selector.return_value = None  # No login
        mock_page.query_selector_all.return_value = [mock_icon]
        
        # Mock button and download
        mock_button = MagicMock()
        mock_page.evaluate_handle.return_value.as_element.return_value = mock_button
        mock_page.expect_download.return_value.__enter__.return_value.value = mock_download
        mock_download.suggested_filename = "existing_file.xlsx"
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        # Should handle duplicate filenames
        assert isinstance(result, dict)

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_download_timeout_error(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test manejo de timeouts en descarga"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        
        # Mock Excel file but download timeout
        mock_icon = MagicMock()
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = [mock_icon]
        
        mock_button = MagicMock()
        mock_page.evaluate_handle.return_value.as_element.return_value = mock_button
        
        # Mock download timeout
        from playwright.sync_api import TimeoutError
        mock_page.expect_download.return_value.__enter__.side_effect = TimeoutError("Download timeout")
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        # Should handle timeout gracefully
        assert isinstance(result, dict)
        assert result['files'] == 0  # No successful downloads


class TestFomagScraperErrorHandling:
    """Tests para manejo de errores específicos."""
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_utf8_configuration_windows(self, mock_makedirs, mock_ensure):
        """Test configuración UTF-8 en Windows"""
        with patch('sys.platform', 'win32'):
            with patch('sys.stdout') as mock_stdout:
                # Should not raise exception even if reconfigure fails
                scraper = FomagScraper(download_dir="/tmp/test")
                assert scraper is not None

    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('app.service.web_scraper.fomag_scraper.sync_playwright')
    def test_missing_context_pages(self, mock_playwright, mock_makedirs, mock_ensure):
        """Test cuando context.pages está vacío"""
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = []  # Empty pages
        mock_context.new_page.return_value = mock_page
        
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []
        
        scraper = FomagScraper(download_dir="/tmp/test")
        
        result = scraper.login_and_download("test_user", "test_pass")
        
        # Should create new page and continue
        mock_context.new_page.assert_called_once()
        assert isinstance(result, dict)


class TestFomagScraperIntegration:
    """Tests de integración."""
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_complete_workflow_structure(self, mock_makedirs, mock_ensure):
        """Test estructura completa del workflow"""
        with patch('app.service.web_scraper.fomag_scraper.sync_playwright') as mock_pw:
            mock_context = MagicMock()
            mock_page = MagicMock()
            
            mock_pw.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_context
            mock_context.pages = [mock_page]
            
            # Mock complete workflow
            mock_page.query_selector.return_value = MagicMock()  # Login form found
            mock_page.query_selector_all.return_value = []  # No Excel files
            
            scraper = FomagScraper(download_dir="/tmp/test")
            result = scraper.login_and_download("user", "pass")
            
            # Verify main workflow steps
            mock_page.goto.assert_called_once()  # Navigate to URL
            mock_page.fill.assert_called()  # Fill credentials
            mock_page.click.assert_called()  # Click buttons for navigation
            
            assert isinstance(result, dict)
            assert all(key in result for key in ['success', 'files', 'message'])

    def test_method_signatures(self):
        """Test que los métodos tienen las firmas correctas"""
        import inspect
        
        # Test login_and_download signature
        sig = inspect.signature(FomagScraper.login_and_download)
        params = list(sig.parameters.keys())
        
        assert 'usuario' in params
        assert 'contraseña' in params
        
        # Test constructor
        init_sig = inspect.signature(FomagScraper.__init__)
        init_params = list(init_sig.parameters.keys())
        
        assert 'download_dir' in init_params
        assert 'progress_callback' in init_params
        assert 'perfil_dir' in init_params

    def test_class_attributes(self):
        """Test atributos de clase importantes"""
        assert hasattr(FomagScraper, '__doc__')
        assert 'Fomag' in FomagScraper.__doc__ or 'Horus' in FomagScraper.__doc__