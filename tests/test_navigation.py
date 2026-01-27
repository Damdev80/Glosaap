"""
Tests para el controlador de navegación (navigation.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del controlador
- Navegación entre vistas
- Gestión de tamaño de ventana
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestNavigationControllerInit:
    """Tests para la inicialización del controlador."""
    
    def test_controller_import(self):
        """Puede importar NavigationController"""
        from app.ui.navigation import NavigationController
        assert NavigationController is not None
    
    def test_controller_is_class(self):
        """NavigationController es una clase"""
        from app.ui.navigation import NavigationController
        assert isinstance(NavigationController, type)
    
    def test_controller_has_docstring(self):
        """El controlador tiene docstring"""
        from app.ui.navigation import NavigationController
        assert NavigationController.__doc__ is not None


class TestNavigationControllerMethods:
    """Tests para métodos del controlador."""
    
    def test_has_go_to_method(self):
        """Tiene método go_to"""
        from app.ui.navigation import NavigationController
        assert hasattr(NavigationController, 'go_to')
    
    def test_has_hide_all_views_method(self):
        """Tiene método _hide_all_views"""
        from app.ui.navigation import NavigationController
        assert hasattr(NavigationController, '_hide_all_views')
    
    def test_has_set_window_size_method(self):
        """Tiene método _set_window_size"""
        from app.ui.navigation import NavigationController
        assert hasattr(NavigationController, '_set_window_size')


class TestNavigationControllerCreation:
    """Tests para creación del controlador con mocks."""
    
    def test_controller_creation(self):
        """Crea el controlador con parámetros mockeados"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_views = {}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        
        assert controller is not None
        assert controller.page is mock_page
        assert controller.views is mock_views
        assert controller.app_state is mock_app_state


class TestNavigationControllerHideViews:
    """Tests para ocultar vistas."""
    
    def test_hide_all_views(self):
        """_hide_all_views oculta todas las vistas"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_view1 = MagicMock()
        mock_view2 = MagicMock()
        mock_views = {"view1": mock_view1, "view2": mock_view2}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        controller._hide_all_views()
        
        mock_view1.hide.assert_called_once()
        mock_view2.hide.assert_called_once()
    
    def test_hide_views_without_hide_method(self):
        """Maneja vistas sin método hide"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_view = Mock(spec=[])  # Sin método hide
        mock_views = {"view1": mock_view}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        # No debería fallar
        controller._hide_all_views()


class TestNavigationControllerSetSize:
    """Tests para establecer tamaño de ventana."""
    
    def test_set_window_size(self):
        """_set_window_size establece dimensiones"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_views = {}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        controller._set_window_size(800, 600)
        
        assert mock_page.window.width == 800
        assert mock_page.window.height == 600


class TestNavigationControllerGoTo:
    """Tests para navegación go_to."""
    
    def test_go_to_updates_current_view(self):
        """go_to actualiza vista actual en app_state"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_view = MagicMock()
        mock_views = {"login": mock_view}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        controller.go_to("login")
        
        assert mock_app_state.current_view == "login"
    
    def test_go_to_shows_view(self):
        """go_to muestra la vista correspondiente"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_view = MagicMock()
        mock_views = {"dashboard": mock_view}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        controller.go_to("dashboard")
        
        mock_view.show.assert_called_once()
    
    def test_go_to_hides_all_views_first(self):
        """go_to oculta todas las vistas primero"""
        from app.ui.navigation import NavigationController
        
        mock_page = MagicMock()
        mock_view1 = MagicMock()
        mock_view2 = MagicMock()
        mock_views = {"view1": mock_view1, "view2": mock_view2}
        mock_app_state = MagicMock()
        
        controller = NavigationController(mock_page, mock_views, mock_app_state)
        controller.go_to("view1")
        
        # Ambas vistas deberían haber sido ocultadas
        mock_view1.hide.assert_called()
        mock_view2.hide.assert_called()


class TestWindowSizesConfig:
    """Tests para configuración de tamaños de ventana."""
    
    def test_window_sizes_imported(self):
        """WINDOW_SIZES se importa correctamente"""
        from app.ui.navigation import WINDOW_SIZES
        assert WINDOW_SIZES is not None
    
    def test_login_size_defined(self):
        """Tamaño de login está definido"""
        from app.ui.navigation import WINDOW_SIZES
        assert "login" in WINDOW_SIZES


class TestNavigationModule:
    """Tests para el módulo de navegación."""
    
    def test_module_has_docstring(self):
        """El módulo tiene docstring"""
        import app.ui.navigation
        assert app.ui.navigation.__doc__ is not None
