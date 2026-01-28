"""
Tests para el scraper base (base_scraper.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del scraper base
- Configuración de directorio de descargas
- Logging de progreso
"""
import pytest
import os
from unittest.mock import Mock, patch
from abc import ABC

from app.service.web_scraper.base_scraper import BaseScraper


class ConcreteScraper(BaseScraper):
    """Implementación concreta para tests."""
    
    def login_and_download(self, **kwargs):
        return {"success": True, "files": 0, "message": "Test"}


class TestBaseScraperInit:
    """Tests para la inicialización del scraper base."""
    
    def test_scraper_creation(self, tmp_path):
        """Crea el scraper correctamente"""
        scraper = ConcreteScraper(download_dir=str(tmp_path))
        assert scraper is not None
    
    def test_scraper_sets_download_dir(self, tmp_path):
        """Establece directorio de descargas"""
        scraper = ConcreteScraper(download_dir=str(tmp_path))
        assert scraper.download_dir == str(tmp_path)
    
    def test_scraper_default_download_dir(self):
        """Directorio por defecto en Desktop"""
        with patch('os.makedirs'):
            scraper = ConcreteScraper()
            assert "descargas_glosaap" in scraper.download_dir
    
    def test_scraper_creates_directory(self, tmp_path):
        """Crea el directorio de descargas"""
        new_dir = tmp_path / "new_downloads"
        scraper = ConcreteScraper(download_dir=str(new_dir))
        assert new_dir.exists()
    
    def test_scraper_sets_progress_callback(self, tmp_path):
        """Establece callback de progreso"""
        callback = Mock()
        scraper = ConcreteScraper(
            download_dir=str(tmp_path),
            progress_callback=callback
        )
        assert scraper.progress_callback is callback
    
    def test_scraper_default_callback_is_print(self, tmp_path):
        """Callback por defecto es print"""
        scraper = ConcreteScraper(download_dir=str(tmp_path))
        assert scraper.progress_callback is print


class TestBaseScraperLog:
    """Tests para logging de progreso."""
    
    def test_log_calls_callback(self, tmp_path):
        """log() llama al callback"""
        callback = Mock()
        scraper = ConcreteScraper(
            download_dir=str(tmp_path),
            progress_callback=callback
        )
        
        scraper.log("Test message")
        
        callback.assert_called_once_with("Test message")
    
    def test_log_with_none_callback_no_error(self, tmp_path):
        """log() con callback None no da error"""
        scraper = ConcreteScraper(download_dir=str(tmp_path))
        scraper.progress_callback = None  # type: ignore
        
        # No debería fallar
        scraper.log("Test")


class TestBaseScraperAbstract:
    """Tests para la naturaleza abstracta."""
    
    def test_is_abstract_class(self):
        """BaseScraper es clase abstracta"""
        assert issubclass(BaseScraper, ABC)
    
    def test_login_and_download_is_abstract(self):
        """login_and_download es método abstracto"""
        assert hasattr(BaseScraper, 'login_and_download')
    
    def test_cannot_instantiate_directly(self, tmp_path):
        """No se puede instanciar directamente"""
        with pytest.raises(TypeError):
            BaseScraper(download_dir=str(tmp_path))  # type: ignore


class TestBaseScraperConcreteImplementation:
    """Tests para implementación concreta."""
    
    def test_concrete_can_be_instantiated(self, tmp_path):
        """Implementación concreta se puede instanciar"""
        scraper = ConcreteScraper(download_dir=str(tmp_path))
        assert scraper is not None
    
    def test_concrete_login_and_download_returns_dict(self, tmp_path):
        """login_and_download retorna dict"""
        scraper = ConcreteScraper(download_dir=str(tmp_path))
        
        result = scraper.login_and_download()
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "files" in result
        assert "message" in result


class TestBaseScraperClass:
    """Tests para la clase en general."""
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert BaseScraper.__doc__ is not None
    
    def test_has_log_method(self):
        """Tiene método log"""
        assert hasattr(BaseScraper, 'log')
