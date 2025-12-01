"""
Vista del Dashboard principal
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES, SPACING


class DashboardView:
    """Vista del dashboard con las 3 cards principales"""
    
    def __init__(self, page: ft.Page, assets_dir: str, on_card_click=None, on_tools_click=None, on_logout=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_card_click = on_card_click
        self.on_tools_click = on_tools_click
        self.on_logout = on_logout
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
            card_container.scale = 1.03 if e.data == "true" else 1.0
            card_container.shadow = ft.BoxShadow(
                spread_radius=2 if e.data == "true" else 1,
                blur_radius=20 if e.data == "true" else 10,
                color=ft.Colors.with_opacity(0.2 if e.data == "true" else 0.1, color),
                offset=ft.Offset(0, 8 if e.data == "true" else 4)
            )
            self.page.update()
        
        def on_click(e):
            if self.on_card_click:
                self.on_card_click(action_key)
        
        card_container = ft.Container(
            content=ft.Column([
                visual_element,
                ft.Container(height=15),
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.W_600,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=5),
                ft.Text(
                    subtitle,
                    size=12,
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            width=200,
            height=220,
            bgcolor=COLORS["bg_white"],
            border_radius=16,
            padding=25,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, color),
                offset=ft.Offset(0, 4)
            ),
            border=ft.border.all(2, ft.Colors.with_opacity(0.3, color)),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
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
                            size=36,
                            weight=ft.FontWeight.W_300,
                            color=COLORS["text_primary"]
                        ),
                        ft.Text(
                            "Sistema de Gestión de Glosas",
                            size=14,
                            color=COLORS["text_secondary"]
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
            )
        ], expand=True, visible=False)
        
        return self.container
    
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
