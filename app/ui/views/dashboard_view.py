"""
Vista del Dashboard principal con soporte de temas
"""
import flet as ft
import os
from app.ui.styles import FONT_SIZES, SPACING, ThemeManager, get_colors, update_colors
from app.config.settings import APP_VERSION
from app.ui.components.loading_overlay import LoadingOverlay, ToastNotification


class DashboardView:
    """Vista del dashboard con las 3 cards principales"""
    
    def __init__(self, page: ft.Page, assets_dir: str, on_card_click=None, on_tools_click=None, on_logout=None, on_web_download=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_card_click = on_card_click
        self.on_tools_click = on_tools_click
        self.on_logout = on_logout
        self.on_web_download = on_web_download
        
        # Componentes de loading
        self.loading_overlay = LoadingOverlay(page)
        self.toast = ToastNotification(page)
        
        self.container = self._build()
        
    def _create_dashboard_card(self, icon, title, subtitle, action_key, image_path=None):
        """Crea una card del dashboard usando Card de Flet (respeta temas)"""
        
        # Decidir si usar imagen o icono
        if image_path and os.path.exists(image_path):
            visual_element = ft.Image(
                src=image_path,
                width=80,
                height=80,
                fit=ft.ImageFit.CONTAIN,
            )
        else:
            visual_element = ft.Container(
                content=ft.Icon(icon, size=50),
                width=80,
                height=80,
                border_radius=40,
                alignment=ft.alignment.center
            )
        
        def on_click(e):
            if self.on_card_click:
                self.on_card_click(action_key)
        
        # Usar Card de Flet que respeta temas automáticamente
        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    visual_element,
                    ft.Container(height=15),
                    ft.Text(
                        title,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        subtitle,
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_400
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                   alignment=ft.MainAxisAlignment.CENTER),
                padding=28,
                width=210,
                height=240,
                on_click=on_click,
                ink=True,
            ),
            elevation=2,
        )
        
        return card
    
    def _build(self):
        """Construye la vista del dashboard"""
        # Crear las 3 cards
        card_evitar = self._create_dashboard_card(
            icon=ft.Icons.SHIELD_OUTLINED,
            title="Evitar Glosa",
            subtitle="Prevención y validación\nantes de facturar",
            action_key="evitar",
            image_path=os.path.join(self.assets_dir, "img", "evitar_glosa.png")
        )
        
        card_manejar = self._create_dashboard_card(
            icon=ft.Icons.BUILD_OUTLINED,
            title="Manejar Glosa",
            subtitle="Gestión y seguimiento\nde glosas activas",
            action_key="manejar",
            image_path=os.path.join(self.assets_dir, "img", "manejar_glosa.png")
        )
        
        card_responder = self._create_dashboard_card(
            icon=ft.Icons.REPLY_ALL_OUTLINED,
            title="Responder Glosa",
            subtitle="Respuesta a objeciones\ny documentación",
            action_key="responder",
            image_path=os.path.join(self.assets_dir, "img", "responder_glosa.png")
        )
        
        # Contenido principal
        main_content = ft.Column([
            ft.Container(height=30),
            # Header
            ft.Column([
                ft.Text("Glosaap", size=40, weight=ft.FontWeight.BOLD),
                ft.Container(height=4),
                ft.Text("Sistema de Gestión de Glosas", size=16, weight=ft.FontWeight.W_400),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=30),
            # Cards
            ft.Row([
                card_evitar,
                card_manejar,
                card_responder
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),
            ft.Container(height=30),
            # Info de usuario
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON_OUTLINE, size=16),
                    ft.Text("Sesión activa", size=12),
                    ft.Container(width=20),
                    ft.TextButton(
                        "Cerrar sesión",
                        on_click=lambda e: self.on_logout() if self.on_logout else None,
                    )
                ], alignment=ft.MainAxisAlignment.CENTER),
                padding=10
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Botones flotantes
        tools_btn = ft.Container(
            content=ft.ElevatedButton(
                content=ft.Row([
                    ft.Image(
                        src=os.path.join(self.assets_dir, "icons", "utils.png"),
                        width=20,
                        height=20,
                        fit=ft.ImageFit.CONTAIN
                    ),
                    ft.Text("Herramientas", size=13, weight=ft.FontWeight.W_500)
                ], spacing=6),
                on_click=lambda e: self.on_tools_click() if self.on_tools_click else None
            ),
            right=20,
            top=15,
        )
        
        web_btn = ft.Container(
            content=ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=20),
                    ft.Text("Descarga Web", size=13, weight=ft.FontWeight.W_500)
                ], spacing=6),
                on_click=lambda e: self.on_web_download() if self.on_web_download else None
            ),
            right=20,
            top=70,
        )
        
        version_btn = ft.Container(
            content=ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14),
                    ft.Text(f"v{APP_VERSION}", size=11)
                ], spacing=4),
                tooltip="Buscar actualizaciones",
                on_click=lambda e: self._check_updates(e)
            ),
            left=10,
            bottom=10,
        )
        
        settings_btn = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.SETTINGS,
                icon_size=22,
                tooltip="Configuración",
                on_click=lambda e: self._open_settings(e),
            ),
            right=15,
            bottom=10,
        )
        
        self.container = ft.Container(
            content=ft.Stack([
                ft.Container(
                    content=main_content,
                    expand=True,
                    alignment=ft.alignment.center,
                ),
                tools_btn,
                web_btn,
                version_btn,
                settings_btn,
            ], expand=True),
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
    
    def _check_updates(self, e):
        """Abre el diálogo de verificación de actualizaciones"""
        try:
            self.show_loading("Verificando actualizaciones...")
            
            if hasattr(self.page, 'data') and self.page.data:
                check_fn = self.page.data.get('check_updates')
                if check_fn:
                    check_fn()
                else:
                    self.show_toast("Función de actualización no disponible", "warning")
            else:
                self.show_toast("No se pudo verificar actualizaciones", "error")
                
        except Exception as ex:
            self.show_toast(f"Error: {str(ex)}", "error")
        finally:
            self.hide_loading()
    
    def _open_settings(self, e):
        """Abre el panel de configuración"""
        is_dark = ThemeManager.is_dark()
        
        def toggle_theme(ev):
            ThemeManager.toggle_theme()
            update_colors()
            self.page.close(settings_dialog)
            # Reconstruir el dashboard
            self.rebuild()
        
        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚙️ Configuración", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Apariencia", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE, size=20),
                        ft.Text("Modo oscuro", size=13),
                        ft.Container(expand=True),
                        ft.Switch(
                            value=is_dark,
                            on_change=toggle_theme,
                        )
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(height=20),
                    ft.Text("Información", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=20),
                        ft.Column([
                            ft.Text(f"Versión: {APP_VERSION}", size=12),
                            ft.Text("Glosaap - Gestión de Glosas", size=11),
                        ], spacing=2)
                    ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ], spacing=5, tight=True),
                width=320,
                padding=ft.padding.only(top=10)
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.page.close(settings_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.open(settings_dialog)
    
    def rebuild(self):
        """Reconstruye el dashboard con el tema actual"""
        was_visible = self.container.visible if self.container else False
        
        # Reconstruir manteniendo visibilidad
        self.container = self._build()
        self.container.visible = was_visible
        self.page.update()
    
    def show(self):
        """Muestra el dashboard"""
        if self.container:
            self.container.visible = True
            self.page.update()
    
    def hide(self):
        """Oculta el dashboard"""
        if self.container:
            self.container.visible = False
            self.page.update()

