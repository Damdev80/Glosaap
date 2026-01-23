"""
Aplicación Glosaap - Cliente IMAP con Flet

Punto de entrada principal de la aplicación.
Versión refactorizada con módulos separados para navegación y lógica de negocio.
"""
import flet as ft
import os
import sys
import logging

# Configurar path para imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Servicios
from app.service.email_service import EmailService

# UI
from app.ui.styles import COLORS, WINDOW_SIZES
from app.ui.screens.eps_screen import EpsScreen
from app.ui.views import DashboardView, LoginView, ToolsView, MessagesView
from app.ui.views.homologacion_view import HomologacionView
from app.ui.views.mix_excel_view import MixExcelView
from app.ui.views.homologador_manual_view import HomologadorManualView
from app.ui.views.web_download_view import WebDownloadView
from app.ui.views.method_selection_view import MethodSelectionView
from app.ui.components.alert_dialog import AlertDialog

# Módulos refactorizados
from app.ui.app_state import AppState
from app.ui.navigation import NavigationController
from app.ui.business_logic import EmailLoader, EPSProcessor, MessageFilter

# Logger
logger = logging.getLogger(__name__)

# Ruta de assets
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))


def main(page: ft.Page):
    """Función principal de la aplicación"""
    
    # ==================== CONFIGURACIÓN INICIAL ====================
    
    page.title = "Glosaap"
    page.window.width = WINDOW_SIZES["login"]["width"]
    page.window.height = WINDOW_SIZES["login"]["height"]
    # Nota: Flet no soporta window_min_width/height directamente
    page.bgcolor = COLORS["bg_white"]
    page.padding = 0
    # Icono de la ventana
    icon_path = os.path.join(ASSETS_DIR, "icons", "app_logo.png")
    if os.path.exists(icon_path):
        page.window.icon = icon_path
    
    # ==================== INICIALIZACIÓN ====================
    
    # Estado global
    app_state = AppState()
    
    # Servicio de email
    email_service = EmailService()
    
    # ==================== CALLBACKS DE NAVEGACIÓN ====================
    
    def handle_login_success():
        """Callback cuando el login es exitoso"""
        nav.go_to_method_selection()
    
    def on_email_method():
        """Callback cuando se selecciona método de correo"""
        nav.go_to_dashboard()
    
    def on_web_method():
        """Callback cuando se selecciona método web"""
        nav.go_to_web_download()
    
    def on_dashboard_action(action_key):
        """Callback cuando se selecciona una acción del dashboard"""
        app_state.dashboard_action = action_key
        nav.go_to_eps_selection()
    
    def on_eps_selected(eps_info, date_from, date_to):
        """Callback cuando se selecciona una EPS"""
        # Guardar estado
        app_state.set_eps(eps_info, date_from, date_to)
        
        logger.info(f"EPS seleccionada: {eps_info.get('name')}")
        
        # Limpiar archivos anteriores
        email_service.clear_attachments()
        
        # Configurar botón de procesamiento
        _configure_process_button(eps_info)
        
        # Navegar y cargar mensajes
        nav.go_to_messages()
        email_loader.load_messages(app_state.get_search_info())
    
    def _configure_process_button(eps_info):
        """Configura el botón de procesamiento según la EPS"""
        eps_filter = (eps_info.get("filter") or "").lower()
        
        if eps_filter == "mutualser":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = "📊 Procesar MUTUALSER"
            messages_view.process_eps_btn.bgcolor = COLORS["primary"]
            messages_view.process_eps_btn.data = "mutualser"
        elif eps_filter == "coosalud":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = "📊 Procesar COOSALUD"
            messages_view.process_eps_btn.bgcolor = COLORS["success"]
            messages_view.process_eps_btn.data = "coosalud"
        else:
            messages_view.show_process_button(False)
    
    def on_download_selected():
        """Callback para descargar mensajes seleccionados"""
        # Esta funcionalidad ya no se usa (descarga automática)
        pass
    
    def on_process_eps():
        """Callback para procesar archivos de EPS"""
        eps_type = messages_view.process_eps_btn.data
        if eps_type:
            eps_processor.process(eps_type)
    
    def on_refresh_messages():
        """Callback para refrescar mensajes"""
        email_loader.load_messages(app_state.get_search_info())
    
    # ==================== CREAR VISTAS ====================
    
    login_view = LoginView(
        page=page,
        email_service=email_service,
        on_login_success=handle_login_success,
        assets_dir=ASSETS_DIR
    )
    
    method_selection_view = MethodSelectionView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_email_method=on_email_method,
        on_web_method=on_web_method,
        on_logout=lambda: nav.go_to_login(logout=True)
    )
    
    dashboard_view = DashboardView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_card_click=on_dashboard_action,
        on_tools_click=lambda: nav.go_to_tools(),
        on_logout=lambda: nav.go_to_login(logout=True),
        on_web_download=lambda: nav.go_to_web_download()
    )
    
    tools_view = ToolsView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_back=lambda: nav.go_to_dashboard(),
        on_homologacion=lambda: nav.go_to_homologacion(),
        on_mix_excel=lambda: nav.go_to_mix_excel(),
        on_homologador_manual=lambda: nav.go_to_homologador_manual()
    )
    
    homologacion_view = HomologacionView(
        page=page,
        on_back=lambda: nav.go_to_tools()
    )
    
    mix_excel_view = MixExcelView(
        page=page,
        on_back=lambda: nav.go_to_tools()
    )
    
    homologador_manual_view = HomologadorManualView(
        page=page,
        on_back=lambda: nav.go_to_tools()
    )
    
    web_download_view = WebDownloadView(
        page=page,
        assets_dir=ASSETS_DIR
    )
    
    messages_view = MessagesView(
        page=page,
        on_back=lambda: nav.go_to_eps_selection(),
        on_refresh=on_refresh_messages,
        on_download_selected=on_download_selected,
        on_process=on_process_eps
    )
    
    eps_screen = EpsScreen(
        page=page,
        on_eps_selected=on_eps_selected,
        on_logout=lambda: nav.go_to_dashboard()
    )
    
    # ==================== CONTROLADORES ====================
    
    # Diccionario de vistas para navegación
    views = {
        "login": login_view,
        "method_selection": method_selection_view,
        "dashboard": dashboard_view,
        "tools": tools_view,
        "homologacion": homologacion_view,
        "mix_excel": mix_excel_view,
        "homologador_manual": homologador_manual_view,
        "web_download": web_download_view,
        "eps": eps_screen,
        "messages": messages_view,
    }
    
    # Controlador de navegación
    nav = NavigationController(page, views, app_state)
    
    # Cargador de emails
    email_loader = EmailLoader(
        email_service=email_service,
        app_state=app_state,
        messages_view=messages_view,
        page=page,
        alert_dialog=AlertDialog
    )
    
    # Procesador de EPS
    eps_processor = EPSProcessor(
        email_service=email_service,
        messages_view=messages_view,
        page=page,
        alert_dialog=AlertDialog
    )
    
    # ==================== CONSTRUIR PÁGINA ====================
    
    # Construir lista de controles (filtrar None)
    controls = [
        login_view.container,
        method_selection_view.container,
        dashboard_view.container,
        tools_view.container,
        homologacion_view.container,
        mix_excel_view.container,
        homologador_manual_view.container,
        web_download_view.container,
        eps_screen.build(),
        messages_view.container
    ]
    
    page.add(
        ft.Stack([c for c in controls if c is not None], expand=True)
    )
    
    # ==================== AUTO-LOGIN ====================
    
    login_view.try_auto_login()


if __name__ == "__main__":
    ft.app(target=main)
