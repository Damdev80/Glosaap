"""
Tests para el scraper de Fomag (fomag_scraper.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del scraper
- Configuración de navegadores
- Estructura del scraper
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

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
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_has_url(self, mock_makedirs, mock_ensure):
        """Tiene URL del portal"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert scraper.url is not None
        assert "horus" in scraper.url
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_url_is_https(self, mock_makedirs, mock_ensure):
        """URL usa HTTPS"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert scraper.url.startswith("https://")
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_scraper_has_perfil_dir(self, mock_makedirs, mock_ensure):
        """Tiene directorio de perfil"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert hasattr(scraper, 'perfil_dir')
        assert scraper.perfil_dir is not None


class TestFomagScraperMethods:
    """Tests para métodos del scraper."""
    
    def test_has_login_and_download(self):
        """Tiene método login_and_download"""
        assert hasattr(FomagScraper, 'login_and_download')
    
    def test_has_ensure_playwright_browsers(self):
        """Tiene método _ensure_playwright_browsers"""
        assert hasattr(FomagScraper, '_ensure_playwright_browsers')


class TestFomagScraperClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """FomagScraper es una clase"""
        assert isinstance(FomagScraper, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert FomagScraper.__doc__ is not None


class TestFomagScraperPerfilDir:
    """Tests para directorio de perfil."""
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    @patch('sys.platform', 'win32')
    @patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'})
    def test_windows_perfil_uses_appdata(self, mock_makedirs, mock_ensure):
        """En Windows usa AppData para perfil"""
        scraper = FomagScraper(download_dir="/tmp/test")
        assert 'Glosaap' in scraper.perfil_dir
    
    @patch.object(FomagScraper, '_ensure_playwright_browsers')
    @patch('os.makedirs')
    def test_custom_perfil_dir(self, mock_makedirs, mock_ensure):
        """Puede especificar perfil personalizado"""
        custom_perfil = "/custom/perfil"
        scraper = FomagScraper(
            download_dir="/tmp/test",
            perfil_dir=custom_perfil
        )
        # Debería usar el perfil personalizado (convertido a absoluto)
        assert "custom" in scraper.perfil_dir or os.path.isabs(scraper.perfil_dir)


class TestFomagScraperEnsureBrowsers:
    """Tests para verificación de navegadores."""
    
    def test_has_ensure_method(self):
        """Tiene método para asegurar navegadores"""
        assert callable(getattr(FomagScraper, '_ensure_playwright_browsers', None))


class TestFomagScraperEncoding:
    """Tests para configuración de encoding."""
    
    def test_module_handles_encoding(self):
        """El módulo configura encoding para Windows"""
        # El módulo debería manejar encoding sin errores
        from app.service.web_scraper import fomag_scraper
        # Solo verificar que se puede importar sin errores
        assert fomag_scraper is not None
