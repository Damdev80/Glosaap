"""
Controlador de navegación de la aplicación Glosaap

Maneja todas las transiciones entre vistas de la aplicación.
"""
import flet as ft
from typing import Dict, Callable, Any
from app.ui.styles import WINDOW_SIZES


class NavigationController:
    """Controlador de navegación entre vistas"""
    
    def __init__(self, page: ft.Page, views: Dict[str, Any], app_state):
        """
        Inicializa el controlador de navegación.
        
        Args:
            page: Página principal de Flet
            views: Diccionario con todas las vistas {nombre: vista}
            app_state: Estado global de la aplicación
        """
        self.page = page
        self.views = views
        self.app_state = app_state
    
    def _hide_all_views(self):
        """Oculta todas las vistas"""
        for view in self.views.values():
            if hasattr(view, 'hide'):
                view.hide()
    
    def _set_window_size(self, width: int, height: int):
        """Establece el tamaño de la ventana"""
        self.page.window_width = width
        self.page.window_height = height
    
    def go_to(self, view_name: str, **kwargs):
        """
        Navega a una vista específica.
        
        Args:
            view_name: Nombre de la vista destino
            **kwargs: Argumentos adicionales para la navegación
        """
        self._hide_all_views()
        self.app_state.current_view = view_name
        
        # Mostrar vista correspondiente
        if view_name in self.views and hasattr(self.views[view_name], 'show'):
            self.views[view_name].show()
        
        # Configurar tamaño de ventana según vista
        sizes = {
            "login": (WINDOW_SIZES["login"]["width"], WINDOW_SIZES["login"]["height"]),
            "method_selection": (900, 600),
            "dashboard": (800, 550),
            "tools": (800, 500),
            "homologacion": (900, 600),
            "mix_excel": (600, 700),
            "homologador_manual": (650, 700),
            "web_download": (1000, 700),
            "eps": (WINDOW_SIZES["main"]["width"], WINDOW_SIZES["main"]["height"]),
            "messages": (WINDOW_SIZES["main"]["width"], WINDOW_SIZES["main"]["height"]),
        }
        
        if view_name in sizes:
            self._set_window_size(*sizes[view_name])
        
        self.page.update()
    
    def go_to_login(self, logout: bool = False):
        """Navega a la pantalla de login"""
        if logout and hasattr(self.views.get("login"), 'logout'):
            self.views["login"].logout()
        self.go_to("login")
    
    def go_to_method_selection(self):
        """Navega a la selección de método"""
        self.go_to("method_selection")
    
    def go_to_dashboard(self):
        """Navega al dashboard"""
        self.go_to("dashboard")
    
    def go_to_tools(self):
        """Navega a herramientas"""
        self.go_to("tools")
    
    def go_to_homologacion(self):
        """Navega a homologación"""
        self.go_to("homologacion")
    
    def go_to_mix_excel(self):
        """Navega a Mix Excel"""
        self.go_to("mix_excel")
    
    def go_to_homologador_manual(self):
        """Navega al homologador manual"""
        self.go_to("homologador_manual")
    
    def go_to_web_download(self):
        """Navega a descarga web"""
        self.go_to("web_download")
    
    def go_to_eps_selection(self):
        """Navega a selección de EPS"""
        self.go_to("eps")
    
    def go_to_messages(self):
        """Navega a mensajes"""
        self.go_to("messages")
    
    def go_back(self):
        """Navega hacia atrás según la vista actual"""
        back_routes = {
            "messages": "eps",
            "eps": "dashboard",
            "tools": "dashboard",
            "mix_excel": "tools",
            "homologador_manual": "tools",
            "homologacion": "tools",
            "web_download": "dashboard",
            "dashboard": "login",
            "method_selection": "login",
        }
        
        current = self.app_state.current_view
        if current in back_routes:
            self.go_to(back_routes[current])
