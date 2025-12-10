"""" 
Componente de tarjeta de EPS
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES, SPACING


class EpsCard:
    """Tarjeta visual para seleccionar una EPS"""
    
    def __init__(self, eps_info: dict, on_click=None):
        """
        Args:
            eps_info: Dict con name, icon, description, filter, filter_type, subject_pattern, image_path
            on_click: Callback al hacer click
        """
        self.eps_info = eps_info
        self.on_click_callback = on_click
    
    def _handle_click(self, e):
        """Maneja el click en la tarjeta"""
        if self.on_click_callback:
            self.on_click_callback(self.eps_info)
    
    def build(self):
        """Construye y retorna la tarjeta"""
        # Decidir si usar imagen o emoji
        image_path = self.eps_info.get("image_path")
        
        if image_path and os.path.exists(image_path):
            # Usar imagen
            visual_element = ft.Image(
                src=image_path,
                width=50,
                height=50,
                fit=ft.ImageFit.CONTAIN
            )
        else:
            # Usar emoji/icono
            visual_element = ft.Text(self.eps_info.get("icon", "📋"), size=36)
        
        def on_hover(e):
            container.scale = 1.05 if e.data == "true" else 1.0
            container.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=16 if e.data == "true" else 10,
                color=ft.Colors.with_opacity(0.12 if e.data == "true" else 0.06, COLORS["text_primary"]),
                offset=ft.Offset(0, 6 if e.data == "true" else 3)
            )
            container.bgcolor = COLORS["hover"] if e.data == "true" else COLORS["bg_white"]
            self.page.update() if hasattr(self, 'page') else None
        
        container = ft.Container(
            content=ft.Column([
                visual_element,
                ft.Text(
                    self.eps_info["name"],
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    self.eps_info.get("description", ""),
                    size=12,
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_400
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            bgcolor=COLORS["bg_white"],
            border_radius=16,
            padding=18,
            width=155,
            height=140,
            ink=True,
            on_click=self._handle_click,
            on_hover=on_hover,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.06, COLORS["text_primary"]),
                offset=ft.Offset(0, 3)
            ),
            border=ft.border.all(1.5, COLORS["border_light"]),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            scale=1.0
        )
        return container