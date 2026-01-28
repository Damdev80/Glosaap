"""
Vista del Dashboard principal
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES, SPACING
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
        
        self.container = self.build()
        
    def _create_dashboard_card(self, icon, title, subtitle, color, action_key, image_path=None):
        """Crea una card del dashboard"""
        
        # Decidir si usar imagen o icono
        if image_path:
            visual_element = ft.Image(
                src=image_path,
                width=80,
                height=80,
                fit=ft.ImageFit.CONTAIN,
            )
        else:
            visual_element = ft.Container(
                content=ft.Icon(icon, size=50, color=COLORS["bg_white"]),
                width=80,
                height=80,
                border_radius=40,
                bgcolor=color,
                alignment=ft.alignment.center
            )
        
        def on_hover(e):
            card_container.scale = 1.05 if e.data == "true" else 1.0
            card_container.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=24 if e.data == "true" else 12,
                color=ft.Colors.with_opacity(0.15 if e.data == "true" else 0.08, COLORS["text_primary"]),
                offset=ft.Offset(0, 8 if e.data == "true" else 4)
            )
            card_container.bgcolor = COLORS["hover"] if e.data == "true" else COLORS["bg_white"]
            self.page.update()
        
        def on_click(e):
            """Maneja el click en la card"""
            if self.on_card_click:
                # Llamar directamente sin loading (el callback decide qué hacer)
                self.on_card_click(action_key)
        
        card_content = ft.Column([
                visual_element,
                ft.Container(height=15),
                ft.Text(
                    title,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=8),
                ft.Text(
                    subtitle,
                    size=13,
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_400
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
        
        card_container = ft.Container(
            content=card_content,
            width=210,
            height=240,
            bgcolor=COLORS["bg_white"],
            border_radius=20,
            padding=28,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=ft.Colors.with_opacity(0.08, COLORS["text_primary"]),
                offset=ft.Offset(0, 4)
            ),
            border=ft.border.all(1.5, COLORS["border_light"]),
            animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_hover=on_hover,
            on_click=on_click,
            ink=True
        )
        
        return card_container
    
    def build(self):
        """Construye la vista del dashboard"""
        # Crear las 3 cards
        card_evitar = self._create_dashboard_card(
            icon=ft.Icons.SHIELD_OUTLINED,
            title="Evitar Glosa",
            subtitle="Prevención y validación\nantes de facturar",
            color="#ffffff",
            action_key="evitar",
            image_path=os.path.join(self.assets_dir, "img", "evitar_glosa.png")
        )
        
        card_manejar = self._create_dashboard_card(
            icon=ft.Icons.BUILD_OUTLINED,
            title="Manejar Glosa",
            subtitle="Gestión y seguimiento\nde glosas activas",
            color="#ffffff",
            action_key="manejar",
            image_path=os.path.join(self.assets_dir, "img", "manejar_glosa.png")
        )
        
        card_responder = self._create_dashboard_card(
            icon=ft.Icons.REPLY_ALL_OUTLINED,
            title="Responder Glosa",
            subtitle="Respuesta a objeciones\ny documentación",
            color="#ffffff",
            action_key="responder",
            image_path=os.path.join(self.assets_dir, "img", "responder_glosa.png")
        )
        
        self.container = ft.Stack([
            # Contenido principal del dashboard
            ft.Container(
                content=ft.Column([
                    ft.Container(height=30),
                    # Header
                    ft.Column([
                        ft.Text(
                            "Glosaap",
                            size=40,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["text_primary"]
                        ),
                        ft.Container(height=4),
                        ft.Text(
                            "Sistema de Gestión de Glosas",
                            size=16,
                            color=COLORS["text_secondary"],
                            weight=ft.FontWeight.W_400
                        ),
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
                            ft.Icon(ft.Icons.PERSON_OUTLINE, size=16, color=COLORS["text_secondary"]),
                            ft.Text(
                                "Sesión activa",
                                size=12,
                                color=COLORS["text_secondary"]
                            ),
                            ft.Container(width=20),
                            ft.TextButton(
                                "Cerrar sesión",
                                on_click=lambda e: self.on_logout() if self.on_logout else None,
                                style=ft.ButtonStyle(color=COLORS["error"])
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        padding=10
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COLORS["bg_light"],
                expand=True,
                alignment=ft.alignment.center,
            ),
            # Botón de Herramientas flotante
            ft.Container(
                content=ft.ElevatedButton(
                    content=ft.Row([
                        ft.Image(
                            src=os.path.join(self.assets_dir, "icons", "utils.png"),
                            width=20,
                            height=20,
                            fit=ft.ImageFit.CONTAIN
                        ),
                        ft.Text("Herramientas", size=13, weight=ft.FontWeight.W_500, color=COLORS["text_primary"])
                    ], spacing=6),
                    bgcolor=COLORS["bg_white"],
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=15, vertical=10),
                        elevation=3,
                        shadow_color=ft.Colors.with_opacity(0.2, "#000000")
                    ),
                    on_click=lambda e: self.on_tools_click() if self.on_tools_click else None
                ),
                right=20,
                top=15,
            ),
            # Botón de Descarga Web flotante
            ft.Container(
                content=ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=20, color=COLORS["primary"]),
                        ft.Text("Descarga Web", size=13, weight=ft.FontWeight.W_500, color=COLORS["primary"])
                    ], spacing=6),
                    bgcolor=COLORS["bg_white"],
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=15, vertical=10),
                        elevation=3,
                        shadow_color=ft.Colors.with_opacity(0.2, "#000000")
                    ),
                    on_click=lambda e: self.on_web_download() if self.on_web_download else None
                ),
                right=20,
                top=70,
            ),
            # Indicador de versión con opción de actualización (esquina inferior izquierda)
            ft.Container(
                content=ft.TextButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=COLORS["text_light"]),
                        ft.Text(f"v{APP_VERSION}", size=11, color=COLORS["text_light"])
                    ], spacing=4),
                    tooltip="Buscar actualizaciones",
                    on_click=lambda e: self._check_updates(e)
                ),
                left=10,
                bottom=10,
            ),
            # Botón de Configuración (esquina inferior derecha)
            ft.Container(
                content=ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    icon_color=COLORS["text_secondary"],
                    icon_size=22,
                    tooltip="Configuración",
                    on_click=lambda e: self._open_settings(e),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.with_opacity(0.1, COLORS["text_secondary"]),
                        shape=ft.CircleBorder(),
                    )
                ),
                right=15,
                bottom=10,
            )
        ], expand=True, visible=False)
        
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
        """Abre el diálogo de verificación de actualizaciones con loading"""
        try:
            self.show_loading("Verificando actualizaciones...")
            
            # Obtener función de verificación desde page.data
            if hasattr(self.page, 'data') and self.page.data:
                check_fn = self.page.data.get('check_updates')
                if check_fn:
                    check_fn()
                else:
                    self.show_toast("Función de actualización no disponible", "warning")
            else:
                self.show_toast("No se pudo verificar actualizaciones", "error")
                
        except Exception as ex:
            self.show_toast(f"Error al verificar actualizaciones: {str(ex)}", "error")
        finally:
            self.hide_loading()
    
    def _open_settings(self, e):
        """Abre el panel de configuración simple"""
        # Obtener versión de la app
        try:
            from app.config.settings import APP_VERSION
        except:
            APP_VERSION = "1.0.0"
        
        # Crear diálogo de configuración simple
        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚙️ Configuración", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    # Sección de Apariencia
                    ft.Text("Apariencia", size=14, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.DARK_MODE, size=20, color=COLORS["text_secondary"]),
                        ft.Text("Tema oscuro", size=13),
                        ft.Container(expand=True),
                        ft.Switch(
                            value=self.page.theme_mode == ft.ThemeMode.DARK if hasattr(self.page, 'theme_mode') else False,
                            on_change=lambda e: self._toggle_theme(e),
                            active_color=COLORS["primary"]
                        )
                    ], alignment=ft.MainAxisAlignment.START),
                    
                    ft.Divider(height=20),
                    
                    # Sección de Información
                    ft.Text("Información", size=14, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=20, color=COLORS["text_secondary"]),
                        ft.Column([
                            ft.Text(f"Versión: {APP_VERSION}", size=12),
                            ft.Text("Desarrollado por Glosaap Team", size=11, color=COLORS["text_light"]),
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
    
    def _close_settings_dialog(self, dialog):
        """Cierra el diálogo de configuración"""
        dialog.open = False
        self.page.update()
    
    def _close_overlay_dialog(self, dialog):
        """Cierra un diálogo del overlay"""
        dialog.open = False
        try:
            self.page.overlay.clear()
        except:
            pass
        self.page.update()
    
    def _toggle_theme(self, e):
        """Cambia el tema de la aplicación"""
        if e.control.value:
            self.page.theme_mode = ft.ThemeMode.DARK
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
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
