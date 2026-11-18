"""
Pruebas para el componente Sidebar y la persistencia de navegación en el shell.
"""
from unittest.mock import MagicMock

import flet as ft

from app.ui.app_state import AppState
from app.ui.components.sidebar import AppSidebar
from app.ui.navigation import NavigationController


class FakePage:
    def __init__(self):
        self.window = MagicMock()
        self.window.maximized = False
        self.window.full_screen = False
        self.overlay = []
        self.client_storage = MagicMock()
        self.client_storage.get.return_value = None

    def update(self):
        pass


def test_sidebar_creation_and_active_states():
    page = FakePage()
    sidebar = AppSidebar(page=page)

    assert sidebar.container is not None
    assert sidebar.current_active_key == "dashboard"

    # Cambiar estado activo a glosas
    sidebar.set_active("eps")
    assert sidebar.current_active_key == "glosas"

    # Cambiar estado activo a tools
    sidebar.set_active("mix_excel")
    assert sidebar.current_active_key == "tools"

    # Cambiar estado activo a web_download
    sidebar.set_active("web_download")
    assert sidebar.current_active_key == "web"


def test_sidebar_flash_glosas():
    page = FakePage()
    sidebar = AppSidebar(page=page)
    # Debe ejecutarse sin errores
    sidebar.flash_glosas(duration=0.05)


def test_navigation_controller_with_shell_and_sidebar():
    page = FakePage()
    ui_state = AppState()

    login_view = MagicMock()
    dashboard_view = MagicMock()
    eps_view = MagicMock()
    tools_view = MagicMock()

    views = {
        "login": login_view,
        "dashboard": dashboard_view,
        "eps": eps_view,
        "tools": tools_view,
    }

    sidebar = AppSidebar(page=page)
    main_shell = ft.Container(visible=False)

    nav = NavigationController(
        page=page,
        views=views,
        app_state=ui_state,
        sidebar=sidebar,
        main_shell=main_shell,
    )

    # 1. Al navegar a dashboard tras login:
    nav.go_to("dashboard")
    assert main_shell.visible is True
    assert ui_state.current_view == "dashboard"
    assert sidebar.current_active_key == "dashboard"
    dashboard_view.show.assert_called_once()
    login_view.hide.assert_called_once()

    # 2. Al navegar a eps (Gestion de Glosas): el shell NO desaparece
    nav.go_to("eps")
    assert main_shell.visible is True  # Sidebar sigue visible
    assert ui_state.current_view == "eps"
    assert sidebar.current_active_key == "glosas"
    eps_view.show.assert_called_once()

    # 3. Al volver hacia atrás (eps -> dashboard):
    nav.go_back()
    assert main_shell.visible is True
    assert ui_state.current_view == "dashboard"
    assert sidebar.current_active_key == "dashboard"

    # 4. Al volver a login (logout): el shell se oculta
    nav.go_to_login(logout=True)
    assert main_shell.visible is False
    assert ui_state.current_view == "login"
