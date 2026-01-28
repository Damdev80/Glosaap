"""
Vista de Herramientas - Con soporte de temas
"""
import flet as ft
import os
from app.ui.styles import FONT_SIZES
from app.ui.components.navigation_header import NavigationHeader
from app.ui.components.loading_overlay import LoadingOverlay, ToastNotification, LoadingButton


class ToolsView:
    """Vista del menú de herramientas"""
    
    def __init__(self, page: ft.Page, assets_dir: str, navigation_controller=None, on_back=None, on_homologacion=None, on_mix_excel=None, on_homologador_manual=None):
        self.page = page
        self.assets_dir = assets_dir
        self.navigation_controller = navigation_controller
        self.on_back = on_back
        self.on_homologacion = on_homologacion
        self.on_mix_excel = on_mix_excel
        self.on_homologador_manual = on_homologador_manual
        self.nav_header = NavigationHeader(page, navigation_controller)
        
        # Componentes de loading
        self.loading_overlay = LoadingOverlay(page)
        self.toast = ToastNotification(page)
        
        self.container = self.build()
        
    def _create_tool_card(self, icon, title, description, color, on_click_action, image_src=None):
        """Crea una card de herramienta usando Card de Flet (respeta temas)"""
        # Contenido del icono: imagen o icono
        if image_src and os.path.exists(image_src):
            icon_content = ft.Image(src=image_src, width=36, height=36, fit=ft.ImageFit.CONTAIN)
        else:
            icon_content = ft.Icon(icon, size=30, color=ft.Colors.ON_PRIMARY)
        
        card = ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=icon_content,
                        width=60,
                        height=60,
                        border_radius=12,
                        bgcolor=color if not image_src else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        alignment=ft.alignment.center
                    ),
                    ft.Container(width=15),
                    ft.Column([
                        ft.Text(title, size=16, weight=ft.FontWeight.W_600),
                        ft.Text(description, size=12)
                    ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
                ]),
                padding=20,
                on_click=on_click_action,
                ink=True,
                width=350
            ),
            elevation=2,
        )
        return card
    
    def build(self):
        """Construye la vista de herramientas"""
        
        # Header con navegación
        header = self.nav_header.build(
            title="⚙️ Herramientas",
            back_text="← Volver al Dashboard",
            breadcrumb=[
                {"text": "Dashboard", "action": lambda e: self.navigation_controller.go_to_dashboard() if self.navigation_controller else None},
                {"text": "Herramientas", "action": None}
            ]
        )
        
        self.container = ft.Container(
            content=ft.Column([
                # Header con navegación
                header,
                # Grid de herramientas
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            self._create_tool_card(
                                ft.Icons.SYNC_ALT,
                                "Gestión Homologación",
                                "Agregar/editar códigos de homologación",
                                "#4CAF50",
                                lambda e: self._handle_homologacion(),
                                image_src=os.path.join(self.assets_dir, "img", "homologar.png")
                            ),
                            self._create_tool_card(
                                ft.Icons.COMPARE_ARROWS,
                                "Mix Excel",
                                "Transferir datos entre archivos Excel",
                                "#2196F3",
                                lambda e: self._handle_mix_excel(),
                                image_src=os.path.join(self.assets_dir, "img", "mix_excel.png")
                            ),
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=15),
                        ft.Row([
                            self._create_tool_card(
                                ft.Icons.TRANSFORM,
                                "Homologador Manual",
                                "Homologar archivos Excel por EPS",
                                "#FF9800",
                                lambda e: self._handle_homologador_manual(),
                                image_src=os.path.join(self.assets_dir, "img", "homologador_manual.png")
                            ),
                            self._create_tool_card(
                                ft.Icons.SETTINGS,
                                "Configuración",
                                "Ajustes de la aplicación",
                                "#9C27B0",
                                lambda e: self._handle_settings()
                            ),
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30,
                    expand=True
                )
            ], spacing=0),
            bgcolor=ft.Colors.SURFACE,
            expand=True,
            visible=False
        )
        
        return self.container
    
    def show_loading(self, message="Cargando..."):
        """Muestra el overlay de carga"""
        if self.loading_overlay:
            self.loading_overlay.show(message)
    
    def hide_loading(self):
        """Oculta el overlay de carga"""
        if self.loading_overlay:
            self.loading_overlay.hide()
    
    def show_toast(self, message, toast_type="success"):
        """Muestra una notificación toast"""
        if self.toast:
            if toast_type == "success":
                self.toast.success(message)
            elif toast_type == "error":
                self.toast.error(message)
            elif toast_type == "warning":
                self.toast.warning(message)
            else:
                self.toast.info(message)
    
    def _handle_homologacion(self):
        """Maneja la navegación a homologación con loading"""
        if self.on_homologacion:
            self.show_loading("Cargando Gestión de Homologación...")
            self.on_homologacion()
    
    def _handle_mix_excel(self):
        """Maneja la navegación a mix excel con loading"""
        if self.on_mix_excel:
            self.show_loading("Cargando Mix Excel...")
            self.on_mix_excel()
    
    def _handle_homologador_manual(self):
        """Maneja la navegación a homologador manual con loading"""
        if self.on_homologador_manual:
            self.show_loading("Cargando Homologador Manual...")
            self.on_homologador_manual()
    
    def _handle_settings(self):
        """Maneja el acceso a configuración"""
        self.show_toast("Configuración - Función en desarrollo", "info")
    
    def show(self):
        """Muestra la vista"""
        if self.container:
            self.container.visible = True
            self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        if self.container:
            self.container.visible = False
            self.page.update()
