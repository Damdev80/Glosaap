"""
Vista de selección de método: Correo vs Web
"""
import flet as ft
import os
from app.ui.styles import COLORS


class MethodSelectionView:
    """Vista para elegir entre descarga por correo o web"""
    
    def __init__(self, page, assets_dir, on_email_method=None, on_web_method=None, on_logout=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_email_method = on_email_method
        self.on_web_method = on_web_method
        self.on_logout = on_logout
        self.container = self._build()
    
    def _create_method_card(self, title, description, action_key, is_primary=True):
        """Crea una card de método"""
        
        def on_hover(e):
            card_container.scale = 1.02 if e.data == "true" else 1.0
            card_container.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=30 if e.data == "true" else 20,
                color=ft.Colors.with_opacity(0.12 if e.data == "true" else 0.08, COLORS["text_primary"]),
                offset=ft.Offset(0, 8 if e.data == "true" else 4)
            )
            self.page.update()
        
        def on_click(e):
            if action_key == "email" and self.on_email_method:
                self.on_email_method()
            elif action_key == "web" and self.on_web_method:
                self.on_web_method()
        
        card_content = ft.Column([
            ft.Text(
                title,
                size=24,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text_primary"],
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(height=15),
            ft.Text(
                description,
                size=14,
                color=COLORS["text_secondary"],
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.W_400
            ),
            ft.Container(height=25),
            ft.Container(
                content=ft.Text(
                    "Seleccionar →",
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=COLORS["primary"] if is_primary else "#4CAF50"
                ),
                alignment=ft.alignment.center
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        
        card_container = ft.Container(
            content=card_content,
            width=320,
            height=220,
            bgcolor=COLORS["bg_white"],
            border_radius=16,
            padding=35,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
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
    
    def _build(self):
        """Construye la interfaz"""
        
        # Header
        header = ft.Column([
            ft.Text(
                "Selecciona el método de descarga",
                size=32,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text_primary"],
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(height=8),
            ft.Text(
                "Elige cómo quieres obtener los archivos de glosas",
                size=15,
                color=COLORS["text_secondary"],
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Cards de métodos
        email_card = self._create_method_card(
            title="Glosa por Correo",
            description="Descarga archivos desde tu bandeja de entrada usando IMAP. Ideal para glosas recibidas vía email.",
            action_key="email",
            is_primary=True
        )
        
        web_card = self._create_method_card(
            title="Glosa por Web",
            description="Descarga automática desde portales web de EPS (Familiar, Fomag). Acceso directo a las plataformas.",
            action_key="web",
            is_primary=False
        )
        
        # Layout
        content = ft.Column([
            ft.Container(height=80),
            header,
            ft.Container(height=50),
            ft.Row([
                email_card,
                ft.Container(width=40),
                web_card
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=50),
            ft.TextButton(
                "Cerrar sesión",
                on_click=lambda e: self.on_logout() if self.on_logout else None,
                style=ft.ButtonStyle(color=COLORS["text_secondary"])
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
        
        return ft.Container(
            content=content,
            expand=True,
            bgcolor=COLORS["bg_light"],
            visible=False
        )
    
    def show(self):
        """Muestra la vista"""
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
