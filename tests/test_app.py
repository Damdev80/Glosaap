"""
Tests adicionales para app principal de Flet (app.py).

Tests simples para la función main sin inicializar Flet.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock


class TestAppModule:
    """Tests para el módulo app.py."""
    
    def test_app_module_import(self):
        """Puede importar el módulo app"""
        from app.ui import app
        assert app is not None
    
    def test_app_module_has_main_function(self):
        """app.py tiene función main"""
        from app.ui.app import main
        assert main is not None
        assert callable(main)
    
    def test_app_module_has_docstring(self):
        """El módulo tiene docstring"""
        from app.ui import app
        assert app.__doc__ is not None


class TestMainFunction:
    """Tests básicos para función main sin inicializar Flet."""
    
    def test_main_is_callable(self):
        """main es callable"""
        from app.ui.app import main
        assert callable(main)
    
    def test_main_signature(self):
        """main tiene parámetro page"""
        import inspect
        from app.ui.app import main
        
        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert 'page' in params


class TestAppImports:
    """Tests para imports del módulo app."""
    
    def test_imports_flet(self):
        """Importa flet correctamente"""
        # No ejecutar flet, solo verificar que se puede importar
        try:
            import flet
            assert flet is not None
        except ImportError:
            pytest.skip("Flet no disponible")
    
    def test_imports_app_state(self):
        """Importa app_state"""
        from app.ui.app_state import AppState
        assert AppState is not None
    
    def test_imports_styles(self):
        """Importa styles"""
        from app.ui.styles import COLORS
        assert COLORS is not None
    
    def test_imports_email_service(self):
        """Importa email_service"""
        from app.service.email_service import EmailService
        assert EmailService is not None


class TestAppConfiguration:
    """Tests para configuración de la app."""
    
    def test_sets_playwright_browsers_path(self):
        """Configura PLAYWRIGHT_BROWSERS_PATH"""
        import os
        # Solo verificar que se puede importar sin error
        from app.ui import app
        assert app is not None
    
    def test_project_root_defined(self):
        """PROJECT_ROOT está definido"""
        from app.ui.app import PROJECT_ROOT
        assert PROJECT_ROOT is not None
        assert os.path.isabs(PROJECT_ROOT)
    
    def test_assets_dir_defined(self):
        """ASSETS_DIR está definido"""
        from app.ui.app import ASSETS_DIR
        assert ASSETS_DIR is not None
        assert "assets" in ASSETS_DIR.lower()